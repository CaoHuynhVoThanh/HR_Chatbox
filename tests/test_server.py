import io
import unittest

from docx import Document
from fastapi.testclient import TestClient

import app.server as server


def docx_bytes(text: str = "Le Thi B - Backend Developer") -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


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
            files={
                "file": (
                    "candidate.docx",
                    docx_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(upload.status_code, 200)
        self.assertEqual(upload.json()["filename"], "candidate.docx")
        self.assertIn("Backend Developer", upload.json()["text"])

    def test_extract_cv_unicode_icon_mapping(self) -> None:
        upload = self.client.post(
            "/api/cv/extract",
            files={
                "file": (
                    "candidate.docx",
                    docx_bytes("\uf095 0123456789"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(upload.status_code, 200)
        self.assertEqual(upload.json()["filename"], "candidate.docx")
        self.assertIn("Phone:", upload.json()["text"])
        self.assertNotIn("\uf095", upload.json()["text"])
