import tempfile
import unittest
from pathlib import Path

from docx import Document

from app.core.cv_extractor import CVExtractionError, extract_cv, resolve_cv_path


class CVExtractorTests(unittest.TestCase):
    def test_extracts_docx_paragraphs_and_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cv_path = Path(tmp_dir) / "candidate.docx"
            document = Document()
            document.add_paragraph("Nguyen Van A - Python Developer")
            table = document.add_table(rows=1, cols=1)
            table.cell(0, 0).text = "FastAPI"
            document.save(cv_path)

            result = extract_cv(cv_path)

        self.assertIn("Python Developer", result.text)
        self.assertIn("FastAPI", result.text)

    def test_requires_explicit_path_when_cv_directory_has_multiple_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            directory = Path(tmp_dir)
            (directory / "a.pdf").touch()
            (directory / "b.docx").touch()
            with self.assertRaises(CVExtractionError):
                resolve_cv_path(None, directory)

