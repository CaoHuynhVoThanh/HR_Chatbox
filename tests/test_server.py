import io
import unittest
from base64 import b64decode
from unittest.mock import patch

from docx import Document
from fastapi.testclient import TestClient

import app.server as server
from app.core.config import Settings


def docx_bytes(text: str = "Le Thi B - Backend Developer") -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def harvard_data() -> dict:
    return {
        "full_name": "Nguyen Van A",
        "headline": "Backend Developer",
        "contact": {"phone": "", "email": "a@example.com", "location": "", "linkedin": "", "website": ""},
        "summary": "Python developer",
        "experience": [],
        "education": [],
        "projects": [],
        "skills": ["Python", "FastAPI"],
        "certifications": [],
    }


class ServerSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(server.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_extract_cv_without_persisting_user_data(self) -> None:
        self.assertEqual(self.client.get("/health").json()["storage"], "browser-session")
        upload = self.client.post(
            "/api/cv/extract",
            files={"file": ("candidate.docx", docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        self.assertEqual(upload.status_code, 200)
        self.assertEqual(upload.json()["filename"], "candidate.docx")
        self.assertIn("Backend Developer", upload.json()["text"])

    @patch("app.server.CVChatService")
    @patch("app.server.get_settings", return_value=Settings("test-key", "gemini-2.5-flash"))
    def test_merge_returns_harvard_markdown_and_a_pdf(self, _, service_class) -> None:
        service_class.return_value.merge_cvs_harvard.return_value = harvard_data()
        response = self.client.post(
            "/api/cv/merge",
            json={
                "primary_cv_text": "Python developer with FastAPI experience",
                "secondary_cv_text": "Backend developer with SQL experience",
                "primary_filename": "backend-profile.pdf",
                "secondary_filename": "candidate.docx",
                "job_context": "Backend Developer",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Nguyen Van A", response.json()["markdown"])
        self.assertEqual(response.json()["template"], "harvard")
        self.assertTrue(b64decode(response.json()["pdf_base64"]).startswith(b"%PDF"))

    @patch("app.server.CVChatService")
    @patch("app.server.get_settings", return_value=Settings("test-key", "gemini-2.5-flash"))
    def test_merge_failure_returns_friendly_chatbot_message(self, _, service_class) -> None:
        service_class.return_value.merge_cvs_harvard.side_effect = RuntimeError("Gemini timeout")
        response = self.client.post(
            "/api/cv/merge",
            json={
                "primary_cv_text": "Primary CV",
                "secondary_cv_text": "Secondary CV",
                "primary_filename": "primary.pdf",
                "secondary_filename": "secondary.pdf",
            },
        )
        self.assertEqual(response.status_code, 502)

    @patch("app.server.CVChatService")
    @patch("app.server.get_settings", return_value=Settings("test-key", "gemini-2.5-flash"))
    def test_format_active_cv_as_harvard(self, _, service_class) -> None:
        service_class.return_value.format_cv_harvard.return_value = harvard_data()
        response = self.client.post(
            "/api/cv/format-harvard",
            json={"cv_text": "Python developer", "filename": "candidate.pdf"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["template"], "harvard")
        self.assertTrue(b64decode(response.json()["pdf_base64"]).startswith(b"%PDF"))

    def test_extract_cv_unicode_icon_mapping(self) -> None:
        upload = self.client.post(
            "/api/cv/extract",
            files={"file": ("candidate.docx", docx_bytes("\uf095 0123456789"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        self.assertEqual(upload.status_code, 200)
        self.assertIn("Phone:", upload.json()["text"])
        self.assertNotIn("\uf095", upload.json()["text"])
