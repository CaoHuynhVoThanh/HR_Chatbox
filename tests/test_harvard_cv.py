import io
import unittest

from pypdf import PdfReader

from app.core.harvard_cv import parse_harvard_cv_json, render_harvard_cv_pdf


class HarvardCVTests(unittest.TestCase):
    def test_missing_fields_default_to_blank_and_render_vietnamese(self) -> None:
        cv = parse_harvard_cv_json('{"full_name": "Nguyễn Văn A", "contact": {"email": "a@example.com"}}')
        self.assertEqual(cv["summary"], "")
        self.assertEqual(cv["contact"]["phone"], "")

        pdf = render_harvard_cv_pdf(cv)
        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)
        self.assertIn("Nguyễn", text)
        self.assertIn("SUMMARY", text)
