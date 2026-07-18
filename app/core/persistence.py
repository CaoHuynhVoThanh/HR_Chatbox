from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class StoredCV:
    id: str
    user_id: str
    original_filename: str
    storage_path: str
    extracted_text: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Conversation:
    id: str
    user_id: str
    cv_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class StoredMessage:
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str


class SQLiteRepository:
    """Persistent storage for CV metadata/text and chat messages.

    File bytes stay in the upload directory; SQLite only stores the private path
    and extracted text used as LLM context.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self):
        """Commit and close every connection (important for SQLite file locks on Windows)."""
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cvs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL UNIQUE,
                    original_filename TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    extracted_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    cv_id TEXT NOT NULL REFERENCES cvs(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
                """
            )

    @staticmethod
    def _cv(row: sqlite3.Row) -> StoredCV:
        return StoredCV(**dict(row))

    @staticmethod
    def _conversation(row: sqlite3.Row) -> Conversation:
        return Conversation(**dict(row))

    @staticmethod
    def _message(row: sqlite3.Row) -> StoredMessage:
        return StoredMessage(**dict(row))

    def get_cv(self, user_id: str) -> StoredCV | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM cvs WHERE user_id = ?", (user_id,)).fetchone()
        return self._cv(row) if row else None

    def upsert_cv(
        self, user_id: str, original_filename: str, storage_path: str, extracted_text: str
    ) -> tuple[StoredCV, str | None]:
        existing = self.get_cv(user_id)
        now = utc_now()
        cv_id = existing.id if existing else str(uuid4())
        created_at = existing.created_at if existing else now
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO cvs (id, user_id, original_filename, storage_path, extracted_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    original_filename = excluded.original_filename,
                    storage_path = excluded.storage_path,
                    extracted_text = excluded.extracted_text,
                    updated_at = excluded.updated_at
                """,
                (cv_id, user_id, original_filename, storage_path, extracted_text, created_at, now),
            )
        record = self.get_cv(user_id)
        assert record is not None
        return record, existing.storage_path if existing else None

    def delete_cv(self, user_id: str) -> str | None:
        existing = self.get_cv(user_id)
        if not existing:
            return None
        with self._connection() as connection:
            connection.execute("DELETE FROM cvs WHERE user_id = ?", (user_id,))
        return existing.storage_path

    def create_conversation(self, user_id: str, cv_id: str) -> Conversation:
        now = utc_now()
        conversation = Conversation(str(uuid4()), user_id, cv_id, now, now)
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO conversations (id, user_id, cv_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conversation.id, conversation.user_id, conversation.cv_id, conversation.created_at, conversation.updated_at),
            )
        return conversation

    def get_conversation(self, conversation_id: str, user_id: str) -> Conversation | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
            ).fetchone()
        return self._conversation(row) if row else None

    def list_conversations(self, user_id: str) -> list[Conversation]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
            ).fetchall()
        return [self._conversation(row) for row in rows]

    def add_message(self, conversation_id: str, role: str, content: str) -> StoredMessage:
        if role not in {"user", "assistant"}:
            raise ValueError("Role must be user or assistant.")
        message = StoredMessage(str(uuid4()), conversation_id, role, content, utc_now())
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (message.id, message.conversation_id, message.role, message.content, message.created_at),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (message.created_at, conversation_id)
            )
        return message

    def list_messages(self, conversation_id: str) -> list[StoredMessage]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at, id", (conversation_id,)
            ).fetchall()
        return [self._message(row) for row in rows]
