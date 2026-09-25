"""
pipeline/extractors/dispatcher.py
===================================
Routes a downloaded file to the correct text extractor based on MIME type
and file extension, then returns normalized List[PageRecord].

Supported formats:
  PDF   → pdf_extractor
  HTML  → html_extractor
  DOCX  → docx_extractor
  CSV   → spreadsheet_extractor
  XLSX  → spreadsheet_extractor
  XLS   → spreadsheet_extractor
  JSON  → inline (each key becomes a field in a PageRecord)
  TXT   → inline (single PageRecord)
  MD    → inline (single PageRecord)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pipeline.core.metadata import ExtractionMethod, LegalDomain, PageRecord
from pipeline.core.logger import get_logger
from pipeline.extractors.csv_extractor_alias import (
    extract_csv,
    extract_xlsx,
    extract_xls,
)
from pipeline.extractors.html_extractor import extract_html_file
from pipeline.extractors.pdf_extractor import extract_pdf
from pipeline.extractors.docx_extractor import extract_docx

log = get_logger("dispatcher")

# Extension → format mapping (lowercase)
_EXT_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".html": "html",
    ".htm": "html",
    ".docx": "docx",
    ".doc": "docx",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".json": "json",
    ".txt": "txt",
    ".md": "txt",
    ".markdown": "txt",
}

# MIME type → format mapping
_MIME_MAP: dict[str, str] = {
    "application/pdf": "pdf",
    "text/html": "html",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "application/json": "json",
    "text/plain": "txt",
    "text/markdown": "txt",
}


def detect_format(path: Path, content_type: Optional[str] = None) -> str:
    """
    Detect the file format from extension and/or MIME type.
    Extension takes precedence.

    Returns:
        Format string: 'pdf', 'html', 'docx', 'csv', 'xlsx', 'xls', 'json', 'txt'

    Raises:
        ValueError: If format cannot be determined.
    """
    ext = path.suffix.lower()
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]
    if content_type:
        mime = content_type.split(";")[0].strip().lower()
        if mime in _MIME_MAP:
            return _MIME_MAP[mime]
    raise ValueError(f"Cannot determine format for: {path} (content-type: {content_type})")


def extract(
    file_path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str = LegalDomain.UNCLASSIFIED.value,
    content_type: Optional[str] = None,
    ocr_mode: str = "inline",
) -> list[PageRecord]:
    """
    Dispatch file_path to the appropriate extractor.

    Args:
        file_path: Path to the raw file (never modified).
        document_id: Document ID to embed in each PageRecord.
        source_url: Original source URL.
        legal_domain: Pre-classified legal domain.
        content_type: Optional HTTP Content-Type header for format detection.
        ocr_mode: 'inline' or 'offline' for PDF OCR.

    Returns:
        List[PageRecord] from the appropriate extractor.

    Raises:
        ValueError: If the file format is unsupported.
        FileNotFoundError: If the file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    fmt = detect_format(file_path, content_type)
    log.info("Dispatching extraction", path=str(file_path), format=fmt, document_id=document_id)

    if fmt == "pdf":
        return extract_pdf(
            file_path,
            document_id=document_id,
            source_url=source_url,
            legal_domain=legal_domain,
            ocr_mode=ocr_mode,
        )
    elif fmt == "html":
        return extract_html_file(
            file_path,
            document_id=document_id,
            source_url=source_url,
            legal_domain=legal_domain,
        )
    elif fmt == "docx":
        return extract_docx(
            file_path,
            document_id=document_id,
            source_url=source_url,
            legal_domain=legal_domain,
        )
    elif fmt == "csv":
        return extract_csv(
            file_path,
            document_id=document_id,
            source_url=source_url,
            legal_domain=legal_domain,
        )
    elif fmt == "xlsx":
        return extract_xlsx(
            file_path,
            document_id=document_id,
            source_url=source_url,
            legal_domain=legal_domain,
        )
    elif fmt == "xls":
        return extract_xls(
            file_path,
            document_id=document_id,
            source_url=source_url,
            legal_domain=legal_domain,
        )
    elif fmt == "json":
        return _extract_json(file_path, document_id=document_id, source_url=source_url, legal_domain=legal_domain)
    elif fmt == "txt":
        return _extract_text(file_path, document_id=document_id, source_url=source_url, legal_domain=legal_domain)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def _extract_json(
    path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str,
) -> list[PageRecord]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(text)
        if isinstance(data, list):
            parts = [json.dumps(item, indent=2, ensure_ascii=False) for item in data[:500]]
        elif isinstance(data, dict):
            parts = [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in data.items()]
        else:
            parts = [text]
    except json.JSONDecodeError:
        parts = [text]

    return [
        PageRecord(
            document_id=document_id,
            page=i + 1,
            text=part,
            source_url=source_url,
            legal_domain=legal_domain,
            extraction_method=ExtractionMethod.JSON_NATIVE,
        )
        for i, part in enumerate(parts)
        if part.strip()
    ]


def _extract_text(
    path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str,
) -> list[PageRecord]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [
        PageRecord(
            document_id=document_id,
            page=1,
            text=text,
            source_url=source_url,
            legal_domain=legal_domain,
            extraction_method=ExtractionMethod.MARKDOWN
            if path.suffix.lower() in (".md", ".markdown")
            else ExtractionMethod.PDF_TEXT,
        )
    ]
