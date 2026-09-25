"""
pipeline/extractors/docx_extractor.py
=======================================
DOCX extraction using python-docx.
Preserves heading hierarchy, paragraphs, and table cell text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pipeline.core.metadata import ExtractionMethod, LegalDomain, PageRecord
from pipeline.core.logger import get_logger

log = get_logger("docx_extractor")


def extract_docx(
    docx_path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str = LegalDomain.UNCLASSIFIED.value,
) -> list[PageRecord]:
    """
    Extract text from a DOCX file.

    Returns one PageRecord per heading-delimited section.
    If no headings are found, returns a single PageRecord with all content.
    """
    try:
        from docx import Document
        from docx.oxml.ns import qn
    except ImportError as e:
        raise ImportError(
            "python-docx is required. Install: pip install python-docx"
        ) from e

    doc = Document(str(docx_path))

    sections: list[dict] = []
    current_heading: Optional[str] = None
    current_parts: list[str] = []

    HEADING_STYLES = {"Heading 1", "Heading 2", "Heading 3", "Heading 4", "Heading 5"}

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        text = para.text.strip()
        if not text:
            continue

        if style_name in HEADING_STYLES:
            if current_parts:
                sections.append({
                    "heading": current_heading,
                    "text": "\n".join(current_parts),
                })
                current_parts = []
            current_heading = text[:200]
        else:
            current_parts.append(text)

    if current_parts:
        sections.append({"heading": current_heading, "text": "\n".join(current_parts)})

    # Also extract tables
    table_texts: list[str] = []
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                table_texts.append(" | ".join(cells))
    if table_texts:
        sections.append({"heading": "Tables", "text": "\n".join(table_texts)})

    if not sections:
        log.warning("DOCX extraction yielded no content", document_id=document_id)
        return []

    records = [
        PageRecord(
            document_id=document_id,
            page=i,
            heading=sec.get("heading"),
            text=sec["text"],
            source_url=source_url,
            legal_domain=legal_domain,
            extraction_method=ExtractionMethod.DOCX,
        )
        for i, sec in enumerate(sections, start=1)
    ]

    log.info("DOCX extraction complete", document_id=document_id, sections=len(records))
    return records
