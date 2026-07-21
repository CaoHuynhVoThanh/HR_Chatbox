import io
import unittest

from pypdf import PdfReader

from app.core.utils import markdown_to_pdf_bytes


class PdfRenderingTests(unittest.TestCase):
    def test_pdf_preserves_vietnamese_unicode(self) -> None:
        source = "# Cao Huỳnh Võ Thanh\n\n**Kỹ năng:** Xử lý dữ liệu tiếng Việt"

        pdf = markdown_to_pdf_bytes(source)
        extracted = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)

        self.assertIn("Huỳnh", extracted)
        self.assertIn("Kỹ năng", extracted)
        self.assertNotIn("■", extracted)
