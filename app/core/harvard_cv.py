"""Harvard-style CV data contract and PDF renderer.

The layout is intentionally a neutral, one-column Harvard-style résumé. It is
not an official Harvard University document or endorsement.
"""

from __future__ import annotations

import json
import re
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from app.core.utils import get_unicode_font_names


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list_of_text(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def _records(value: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    records: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        record = {field: _text(item.get(field)) for field in fields if field != "bullets"}
        if "bullets" in fields:
            record["bullets"] = _list_of_text(item.get("bullets"))
        records.append(record)
    return records


def parse_harvard_cv_json(raw: str) -> dict[str, Any]:
    """Validate the JSON contract emitted by Gemini and default missing fields."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini không trả về dữ liệu CV Harvard hợp lệ.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Dữ liệu CV Harvard phải là một đối tượng JSON.")

    return {
        "full_name": _text(payload.get("full_name")),
        "headline": _text(payload.get("headline")),
        "contact": {
            key: _text(payload.get("contact", {}).get(key)) if isinstance(payload.get("contact"), dict) else ""
            for key in ("phone", "email", "location", "linkedin", "website")
        },
        "summary": _text(payload.get("summary")),
        "experience": _records(
            payload.get("experience"),
            ("title", "organization", "location", "dates", "bullets"),
        ),
        "education": _records(
            payload.get("education"),
            ("degree", "institution", "location", "dates", "details"),
        ),
        "projects": _records(payload.get("projects"), ("name", "dates", "details", "bullets")),
        "skills": _list_of_text(payload.get("skills")),
        "certifications": _list_of_text(payload.get("certifications")),
    }


def harvard_cv_to_markdown(cv: dict[str, Any]) -> str:
    """A chat-friendly preview of the exact fields rendered into the PDF."""
    lines = [f"# {cv['full_name']}", cv["headline"], "", "## Contact"]
    contact = [f"{label}: {cv['contact'][key]}" for key, label in (("phone", "Phone"), ("email", "Email"), ("location", "Location"), ("linkedin", "LinkedIn"), ("website", "Website"))]
    lines.append(" · ".join(contact))
    lines.extend(["", "## Summary", cv["summary"], "", "## Experience"])
    for item in cv["experience"]:
        heading = " | ".join(value for value in (item["title"], item["organization"], item["dates"]) if value)
        lines.append(f"### {heading}")
        lines.extend(f"- {bullet}" for bullet in item["bullets"])
    lines.extend(["", "## Education"])
    for item in cv["education"]:
        lines.append(" | ".join(value for value in (item["degree"], item["institution"], item["dates"]) if value))
    lines.extend(["", "## Projects"])
    for item in cv["projects"]:
        lines.append(f"### {item['name']}")
        lines.append(item["details"])
        lines.extend(f"- {bullet}" for bullet in item["bullets"])
    lines.extend(["", "## Skills", " · ".join(cv["skills"]), "", "## Certifications"])
    lines.extend(cv["certifications"])
    return "\n".join(lines).strip()


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    # Paragraph accepts a small HTML subset; escape user/LLM data to avoid
    # accidental markup changing the generated document.
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(escaped or "&nbsp;", style)


def render_harvard_cv_pdf(cv: dict[str, Any]) -> bytes:
    """Render structured CV data into the local Harvard-style PDF template."""
    regular_font, bold_font = get_unicode_font_names()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=(cv["full_name"] or "CV Harvard"),
    )
    base = getSampleStyleSheet()
    name = ParagraphStyle("HarvardName", parent=base["Title"], fontName=bold_font, fontSize=19, leading=23, alignment=TA_CENTER)
    headline = ParagraphStyle("HarvardHeadline", parent=base["Normal"], fontName=regular_font, fontSize=10, leading=13, alignment=TA_CENTER)
    contact_style = ParagraphStyle("HarvardContact", parent=headline, fontSize=8.8, leading=11, textColor=colors.HexColor("#313131"))
    section = ParagraphStyle("HarvardSection", parent=base["Heading2"], fontName=bold_font, fontSize=10.5, leading=14, textColor=colors.HexColor("#8A2432"), spaceBefore=8, spaceAfter=3)
    item_title = ParagraphStyle("HarvardItem", parent=base["Normal"], fontName=bold_font, fontSize=9.5, leading=12)
    body = ParagraphStyle("HarvardBody", parent=base["Normal"], fontName=regular_font, fontSize=9.2, leading=12, spaceAfter=2)
    bullet = ParagraphStyle("HarvardBullet", parent=body, leftIndent=11, firstLineIndent=-7, bulletIndent=4, spaceAfter=1)
    blank = Spacer(1, 11 * mm)

    contact_line = "  |  ".join(
        f"{label}: {cv['contact'][key] or '____________'}"
        for key, label in (
            ("phone", "Phone"),
            ("email", "Email"),
            ("location", "Location"),
            ("linkedin", "LinkedIn"),
            ("website", "Website"),
        )
    )
    story: list[Any] = [
        _paragraph(cv["full_name"], name),
        _paragraph(cv["headline"], headline),
        _paragraph(contact_line, contact_style),
        Spacer(1, 3 * mm),
        HRFlowable(width="100%", thickness=1.3, color=colors.HexColor("#8A2432"), spaceAfter=3),
    ]

    def add_section(label: str, contents: list[Any]) -> None:
        story.append(_paragraph(label, section))
        story.append(HRFlowable(width="100%", thickness=0.35, color=colors.HexColor("#B8B8B8"), spaceAfter=3))
        story.extend(contents or [blank])

    add_section("SUMMARY", [_paragraph(cv["summary"], body)] if cv["summary"] else [])

    experience_content: list[Any] = []
    for item in cv["experience"]:
        title = " | ".join(value for value in (item["title"], item["organization"], item["dates"]) if value)
        experience_content.append(_paragraph(title, item_title))
        if item["location"]:
            experience_content.append(_paragraph(item["location"], body))
        experience_content.extend(_paragraph(f"• {point}", bullet) for point in item["bullets"])
        experience_content.append(Spacer(1, 2 * mm))
    add_section("EXPERIENCE", experience_content)

    education_content: list[Any] = []
    for item in cv["education"]:
        education_content.append(_paragraph(" | ".join(value for value in (item["degree"], item["institution"], item["dates"]) if value), item_title))
        details = " | ".join(value for value in (item["location"], item["details"]) if value)
        if details:
            education_content.append(_paragraph(details, body))
        education_content.append(Spacer(1, 2 * mm))
    add_section("EDUCATION", education_content)

    project_content: list[Any] = []
    for item in cv["projects"]:
        project_content.append(_paragraph(" | ".join(value for value in (item["name"], item["dates"]) if value), item_title))
        if item["details"]:
            project_content.append(_paragraph(item["details"], body))
        project_content.extend(_paragraph(f"• {point}", bullet) for point in item["bullets"])
        project_content.append(Spacer(1, 2 * mm))
    add_section("PROJECTS", project_content)
    add_section("SKILLS", [_paragraph(" · ".join(cv["skills"]), body)] if cv["skills"] else [])
    add_section("CERTIFICATIONS", [_paragraph(" · ".join(cv["certifications"]), body)] if cv["certifications"] else [])

    document.build(story)
    result = buffer.getvalue()
    buffer.close()
    return result
