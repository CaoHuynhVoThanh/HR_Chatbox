import io
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from docx import Document
from fastapi.testclient import TestClient

import app.server as server
from app.core.persistence import SQLiteRepository


def docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("Le Thi B - Backend Developer")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class ServerPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        root = Path(self.temp_directory.name)
        server.UPLOADS_DIRECTORY = root / "uploads"
        server.repository = SQLiteRepository(root / "hr_chatbot.db")
        self.client = TestClient(server.app)
        self.client.__enter__()
        self.headers = {"X-User-ID": str(uuid4())}

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_directory.cleanup()

    def test_upload_cv_and_create_persistent_conversation(self) -> None:
        upload = self.client.post(
            "/api/cv",
            headers=self.headers,
            files={
                "file": (
                    "candidate.docx",
                    docx_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(upload.status_code, 201)
        self.assertEqual(upload.json()["filename"], "candidate.docx")

        duplicate = self.client.post(
            "/api/cv",
            headers=self.headers,
            files={"file": ("other.docx", docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        self.assertEqual(duplicate.status_code, 409)

        created = self.client.post("/api/conversations", headers=self.headers)
        self.assertEqual(created.status_code, 201)
        conversation_id = created.json()["id"]

        messages = self.client.get(f"/api/conversations/{conversation_id}/messages", headers=self.headers)
        self.assertEqual(messages.status_code, 200)
        self.assertEqual(messages.json(), [])
        self.assertEqual(len(server.repository.list_conversations(self.headers["X-User-ID"])), 1)

