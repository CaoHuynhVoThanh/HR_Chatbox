"""FastAPI backend for persistent CVs and conversations.

Authentication is intentionally out of scope for this prototype. The browser must
send a UUID in X-User-ID (stored locally); production must derive this ID from an
authenticated session/JWT instead of trusting a request header.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core.chat_service import CVChatService
from app.core.config import get_backend_settings, get_settings
from app.core.cv_extractor import CVDocument, CVExtractionError, SUPPORTED_EXTENSIONS, extract_cv
from app.core.persistence import Conversation, SQLiteRepository, StoredCV, StoredMessage

backend_settings = get_backend_settings()
DATABASE_PATH = backend_settings.database_path
UPLOADS_DIRECTORY = backend_settings.uploads_directory
ALLOWED_ORIGINS = backend_settings.allowed_origins
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

repository = SQLiteRepository(DATABASE_PATH)


@asynccontextmanager
async def lifespan(_: FastAPI):
    UPLOADS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    repository.initialize()
    yield


app = FastAPI(
    title="HR CV Chatbot API",
    version="0.1.0",
    description="Persistent CV upload and chat API for the HR CV Coach.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-User-ID"],
)


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=12_000)


def current_user_id(x_user_id: str = Header(alias="X-User-ID")) -> str:
    """Validate the temporary browser identity and normalize its representation."""
    try:
        return str(UUID(x_user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-ID phải là UUID hợp lệ.",
        ) from exc


def cv_payload(cv: StoredCV) -> dict[str, str | int]:
    return {
        "id": cv.id,
        "filename": cv.original_filename,
        "text_length": len(cv.extracted_text),
        "created_at": cv.created_at,
        "updated_at": cv.updated_at,
    }


def conversation_payload(conversation: Conversation) -> dict[str, str]:
    return {
        "id": conversation.id,
        "cv_id": conversation.cv_id,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


def message_payload(message: StoredMessage) -> dict[str, str]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }


def require_cv(user_id: str) -> StoredCV:
    cv = repository.get_cv(user_id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng chưa tải CV lên.")
    return cv


def require_conversation(conversation_id: str, user_id: str) -> Conversation:
    conversation = repository.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc hội thoại.")
    return conversation


def message_pairs(messages: list[StoredMessage]) -> list[tuple[str, str]]:
    """Convert durable messages into the paired history accepted by the current chat service."""
    pairs: list[tuple[str, str]] = []
    pending_user: str | None = None
    for message in messages:
        if message.role == "user":
            pending_user = message.content
        elif pending_user is not None:
            pairs.append((pending_user, message.content))
            pending_user = None
    return pairs


def remove_stored_file(storage_path: str | None) -> None:
    if not storage_path:
        return
    root = UPLOADS_DIRECTORY.resolve()
    candidate = Path(storage_path).resolve()
    if root in candidate.parents:
        candidate.unlink(missing_ok=True)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/cv")
def get_cv(user_id: str = Depends(current_user_id)) -> dict[str, str | int]:
    return cv_payload(require_cv(user_id))


@app.post("/api/cv", status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(description="One CV in PDF or DOCX format"),
    replace: bool = False,
    user_id: str = Depends(current_user_id),
) -> dict[str, str | int]:
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Chỉ nhận tệp .pdf hoặc .docx.")
    if repository.get_cv(user_id) and not replace:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Người dùng đã có CV. Dùng ?replace=true để thay thế CV hiện tại.",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CV vượt quá giới hạn 10 MB.")

    user_directory = UPLOADS_DIRECTORY / user_id
    user_directory.mkdir(parents=True, exist_ok=True)
    stored_path = user_directory / f"{uuid4()}{extension}"
    try:
        stored_path.write_bytes(content)
        extracted = extract_cv(stored_path)
        record, previous_path = repository.upsert_cv(
            user_id=user_id,
            original_filename=Path(filename).name,
            storage_path=str(stored_path),
            extracted_text=extracted.text,
        )
    except CVExtractionError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise

    remove_stored_file(previous_path)
    return cv_payload(record)


@app.delete("/api/cv", status_code=status.HTTP_204_NO_CONTENT)
def delete_cv(user_id: str = Depends(current_user_id)) -> None:
    storage_path = repository.delete_cv(user_id)
    if not storage_path:
        raise HTTPException(status_code=404, detail="Người dùng chưa có CV để xóa.")
    remove_stored_file(storage_path)


@app.post("/api/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(user_id: str = Depends(current_user_id)) -> dict[str, str]:
    cv = require_cv(user_id)
    return conversation_payload(repository.create_conversation(user_id, cv.id))


@app.get("/api/conversations")
def list_conversations(user_id: str = Depends(current_user_id)) -> list[dict[str, str]]:
    return [conversation_payload(conversation) for conversation in repository.list_conversations(user_id)]


@app.get("/api/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str, user_id: str = Depends(current_user_id)) -> list[dict[str, str]]:
    require_conversation(conversation_id, user_id)
    return [message_payload(message) for message in repository.list_messages(conversation_id)]


@app.post("/api/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: str,
    request: ChatRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, dict[str, str]]:
    conversation = require_conversation(conversation_id, user_id)
    cv = require_cv(user_id)
    text = request.content.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Nội dung tin nhắn không được để trống.")

    history = message_pairs(repository.list_messages(conversation.id))
    user_message = repository.add_message(conversation.id, "user", text)
    try:
        service = CVChatService(
            settings=get_settings(),
            cv=CVDocument(path=Path(cv.storage_path), text=cv.extracted_text),
            history=history,
        )
        answer = service.reply(text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Gemini không thể tạo phản hồi. Hãy thử lại sau.") from exc

    assistant_message = repository.add_message(conversation.id, "assistant", answer)
    return {"user_message": message_payload(user_message), "assistant_message": message_payload(assistant_message)}
