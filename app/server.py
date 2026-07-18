"""Stateless FastAPI backend for the browser-session HR CV Coach.

The browser owns all user data in sessionStorage. This server never writes a CV
or conversation to a database or upload directory; it only processes request data
and temporarily writes a CV while extracting its text.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.chat_service import CVChatService
from app.core.config import get_backend_settings, get_settings
from app.core.cv_extractor import CVDocument, CVExtractionError, SUPPORTED_EXTENSIONS, extract_cv

backend_settings = get_backend_settings()
MAX_UPLOAD_BYTES = 3 * 1024 * 1024
MAX_CV_TEXT_CHARS = 100_000
STATIC_DIRECTORY = Path(__file__).parent / "static"

app = FastAPI(
    title="HR CV Chatbot API",
    version="0.2.0",
    description="Stateless API. The browser stores CV and conversation data in sessionStorage.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=backend_settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class HistoryTurn(BaseModel):
    user: str = Field(min_length=1, max_length=12_000)
    assistant: str = Field(min_length=1, max_length=12_000)


class ChatRequest(BaseModel):
    cv_text: str = Field(min_length=1, max_length=MAX_CV_TEXT_CHARS)
    content: str = Field(min_length=1, max_length=12_000)
    history: list[HistoryTurn] = Field(default_factory=list, max_length=20)


@app.get("/", include_in_schema=False)
def web_client() -> FileResponse:
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "storage": "browser-session"}


@app.post("/api/cv/extract")
async def extract_uploaded_cv(
    file: UploadFile = File(description="One CV in PDF or DOCX format"),
) -> dict[str, str | int]:
    """Extract CV text without retaining the uploaded file after the response."""
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Chỉ nhận tệp .pdf hoặc .docx.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="CV vượt quá 3 MB để phù hợp giới hạn sessionStorage của trình duyệt.",
        )

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)
        cv = extract_cv(temporary_path)
    except CVExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)

    return {"filename": Path(filename).name, "text": cv.text, "text_length": len(cv.text)}


@app.post("/api/chat", status_code=status.HTTP_200_OK)
def chat(request: ChatRequest) -> dict[str, str]:
    """Generate a response using context supplied from browser sessionStorage."""
    content = request.content.strip()
    cv_text = request.cv_text.strip()
    if not content or not cv_text:
        raise HTTPException(status_code=422, detail="CV và nội dung tin nhắn không được để trống.")

    try:
        service = CVChatService(
            settings=get_settings(),
            cv=CVDocument(path=Path("browser-session-cv"), text=cv_text),
            history=[(turn.user, turn.assistant) for turn in request.history],
        )
        answer = service.reply(content)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Gemini không thể tạo phản hồi. Hãy thử lại sau.") from exc
    return {"assistant": answer}
