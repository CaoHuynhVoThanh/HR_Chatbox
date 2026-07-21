from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from os import getenv
from pathlib import Path

from markdown import markdown
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

PDF_FONT_NAME = "CVUnicode"
PDF_BOLD_FONT_NAME = "CVUnicode-Bold"


def _first_existing_path(paths: list[str | Path | None]) -> Path | None:
    for value in paths:
        if value and Path(value).is_file():
            return Path(value)
    return None


@lru_cache(maxsize=1)
def _unicode_font_paths() -> tuple[Path, Path]:
    """Locate a TrueType font with Vietnamese glyphs.

    A deployer can set PDF_FONT_PATH and PDF_BOLD_FONT_PATH. The remaining
    locations cover normal Windows, Linux, and macOS installations.
    """
    regular_path = _first_existing_path(
        [
            getenv("PDF_FONT_PATH"),
            r"C:\\Windows\\Fonts\\arial.ttf",
            r"C:\\Windows\\Fonts\\calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
    )
    bold_path = _first_existing_path(
        [
            getenv("PDF_BOLD_FONT_PATH"),
            r"C:\\Windows\\Fonts\\arialbd.ttf",
            r"C:\\Windows\\Fonts\\calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    )
    if not regular_path:
        raise RuntimeError(
            "Không tìm thấy font Unicode để tạo PDF. Hãy cấu hình PDF_FONT_PATH tới font .ttf hỗ trợ tiếng Việt."
        )
    return regular_path, bold_path or regular_path


@lru_cache(maxsize=1)
def _register_unicode_fonts() -> tuple[str, str]:
    """Register the Unicode font for ReportLab PDF output."""
    regular_path, bold_path = _unicode_font_paths()

    pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(regular_path)))
    pdfmetrics.registerFont(TTFont(PDF_BOLD_FONT_NAME, str(bold_path)))
    pdfmetrics.registerFontFamily(
        PDF_FONT_NAME,
        normal=PDF_FONT_NAME,
        bold=PDF_BOLD_FONT_NAME,
        italic=PDF_FONT_NAME,
        boldItalic=PDF_BOLD_FONT_NAME,
    )
    return PDF_FONT_NAME, PDF_BOLD_FONT_NAME


def get_unicode_font_names() -> tuple[str, str]:
    """Return registered regular/bold Unicode font names for PDF renderers."""
    return _register_unicode_fonts()


def markdown_to_pdf_bytes(md_text: str) -> bytes:
    """Render a Unicode-safe plain PDF when no PDF template is available."""
    regular_font, bold_font = _register_unicode_fonts()
    html = markdown(md_text)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = regular_font
    styles["Normal"].boldFontName = bold_font
    styles["Normal"].italicFontName = regular_font
    styles["Normal"].boldItalicFontName = bold_font
    story: list[Paragraph] = []

    if len(html) < 2000:
        story.append(Paragraph(html, styles["Normal"]))
    else:
        for part in html.split("</p>"):
            if not part.strip():
                continue
            text = part + ("</p>" if not part.strip().endswith("</p>") else "")
            story.append(Paragraph(text, styles["Normal"]))
            story.append(Spacer(1, 6))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

