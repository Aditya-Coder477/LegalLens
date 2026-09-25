"""
pipeline/extractors/pdf_extractor.py
=====================================
PDF text extraction with automatic scanned-page detection and OCR fallback.

Strategy:
  1. Use pdfminer.six to extract text from each page
  2. Count characters per page
  3. If avg chars < min_chars_per_page threshold → page is scanned
  4. Scanned pages: convert to image via pdf2image → OCR via pytesseract
  5. Mixed PDFs: apply OCR only to scanned pages (page-by-page granularity)
  6. Original PDF is NEVER modified

OCR metadata recorded per-page:
  - ocr_used, ocr_engine, ocr_language, ocr_confidence (avg word confidence)

Rules:
  - Never execute PDF content (read-only, no JavaScript, no actions)
  - Never modify the original file
  - If pdfminer or pytesseract are not installed → raise ImportError clearly
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from pipeline.core.config import get_config
from pipeline.core.logger import get_logger
from pipeline.core.metadata import ExtractionMethod, LegalDomain, PageRecord

log = get_logger("pdf_extractor")


def _extract_digital_text_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """
    Extract (page_number, text) pairs from a digital-text PDF using pdfminer.six.
    Page numbers are 1-indexed.
    """
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextBox
    except ImportError as e:
        raise ImportError(
            "pdfminer.six is required for PDF extraction. "
            "Install it with: pip install pdfminer.six"
        ) from e

    pages: list[tuple[int, str]] = []
    try:
        for page_num, layout in enumerate(extract_pages(str(pdf_path)), start=1):
            page_text_parts: list[str] = []
            for element in layout:
                if isinstance(element, LTTextBox):
                    page_text_parts.append(element.get_text())
            pages.append((page_num, "\n".join(page_text_parts)))
    except Exception as exc:
        log.error("pdfminer extraction failed", path=str(pdf_path), error=str(exc))
        raise
    return pages


def _ocr_page(pdf_path: Path, page_num: int, dpi: int, lang: str) -> tuple[str, Optional[float]]:
    """
    OCR a single PDF page using pdf2image + pytesseract.
    Returns (text, avg_confidence).
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as e:
        raise ImportError(
            "pdf2image and pytesseract are required for OCR. "
            "Install: pip install pdf2image pytesseract"
        ) from e

    images = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        first_page=page_num,
        last_page=page_num,
        fmt="jpeg",
    )
    if not images:
        return "", None

    img = images[0]
    # Get word-level confidence data
    data = pytesseract.image_to_data(
        img,
        lang=lang,
        output_type=pytesseract.Output.DICT,
    )
    # Collect words and confidences
    words = []
    confidences = []
    for i, word in enumerate(data["text"]):
        conf = int(data["conf"][i])
        if conf >= 0 and word.strip():
            words.append(word)
            confidences.append(conf)

    text = " ".join(words)
    avg_conf = sum(confidences) / len(confidences) if confidences else None
    return text, avg_conf


def _detect_headings(text: str) -> Optional[str]:
    """
    Heuristic heading detection: look for numbered section patterns.
    Returns the section heading if detected, else None.
    """
    patterns = [
        r"^(?:Section|SEC\.?|S\.)\s*(\d+[A-Z]?(?:\.\d+)?)",  # Section 42A
        r"^(\d+[A-Z]?\.\s+[A-Z][A-Za-z ]{4,50})\s*$",         # "8. Definitions"
        r"^(CHAPTER\s+[IVXLCDM0-9]+)",                          # CHAPTER I
        r"^(PART\s+[IVXLCDM0-9A-Z]+)",                          # PART III
    ]
    for line in text.splitlines()[:5]:
        line = line.strip()
        for pat in patterns:
            m = re.match(pat, line, re.IGNORECASE)
            if m:
                return line[:120]
    return None


def _detect_section_number(text: str) -> Optional[str]:
    """Extract the section number from page text if present."""
    patterns = [
        r"^(?:Section|SEC\.?)\s*(\d+[A-Z]?(?:\.\d+)?)",
        r"^\s*(\d+[A-Z]?)\.\s+[A-Z]",
    ]
    for line in text.splitlines()[:3]:
        for pat in patterns:
            m = re.match(pat, line.strip(), re.IGNORECASE)
            if m:
                return m.group(1)
    return None


def extract_pdf(
    pdf_path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str = LegalDomain.UNCLASSIFIED.value,
    min_chars_per_page: Optional[int] = None,
    ocr_lang: Optional[str] = None,
    ocr_dpi: int = 300,
    ocr_mode: str = "inline",
) -> list[PageRecord]:
    """
    Extract text from a PDF file, applying OCR page-by-page where needed.

    Args:
        pdf_path: Path to the raw PDF (never modified).
        document_id: The document_id to embed in each PageRecord.
        source_url: Original source URL for provenance.
        legal_domain: Pre-classified domain string.
        min_chars_per_page: Pages with fewer chars trigger OCR. Default from config.
        ocr_lang: Tesseract language code. Default from config.
        ocr_dpi: DPI for pdf2image. Default 300.
        ocr_mode: 'inline' to OCR now, 'offline' to skip OCR and mark for later.

    Returns:
        List of PageRecord objects (one per page).
    """
    cfg = get_config()
    if min_chars_per_page is None:
        min_chars_per_page = cfg.ocr.min_chars_per_page
    if ocr_lang is None:
        ocr_lang = cfg.ocr.tesseract_lang

    log.info("Extracting PDF", path=str(pdf_path), document_id=document_id)
    raw_pages = _extract_digital_text_pages(pdf_path)

    records: list[PageRecord] = []
    for page_num, text in raw_pages:
        char_count = len(text.strip())
        is_scanned = char_count < min_chars_per_page

        ocr_used = False
        ocr_confidence: Optional[float] = None
        extraction_method = ExtractionMethod.PDF_TEXT

        if is_scanned:
            if ocr_mode == "offline":
                # Mark as needing OCR but don't process now
                log.info(
                    "Scanned page deferred for offline OCR",
                    document_id=document_id, page=page_num,
                )
                extraction_method = ExtractionMethod.PDF_OCR
                ocr_used = True
                # text remains the (empty/sparse) pdfminer extraction
            else:
                # Inline OCR
                log.log_ocr(document_id=document_id, page=page_num, confidence=None)
                try:
                    text, ocr_confidence = _ocr_page(pdf_path, page_num, ocr_dpi, ocr_lang)
                    ocr_used = True
                    extraction_method = ExtractionMethod.PDF_OCR
                    log.log_ocr(document_id=document_id, page=page_num, confidence=ocr_confidence)
                except Exception as exc:
                    log.error(
                        "OCR failed for page",
                        document_id=document_id, page=page_num, error=str(exc)
                    )

        heading = _detect_headings(text)
        section_number = _detect_section_number(text)

        # Determine if this was a mixed page (had some text but still needed OCR)
        if not is_scanned and ocr_used:
            extraction_method = ExtractionMethod.PDF_MIXED

        records.append(
            PageRecord(
                document_id=document_id,
                page=page_num,
                section=section_number,
                heading=heading,
                text=text,
                source_url=source_url,
                legal_domain=legal_domain,
                ocr_used=ocr_used,
                ocr_confidence=ocr_confidence,
                ocr_engine="tesseract" if ocr_used else None,
                ocr_language=ocr_lang if ocr_used else None,
                extraction_method=extraction_method,
            )
        )

    log.info(
        "PDF extraction complete",
        document_id=document_id,
        total_pages=len(records),
        ocr_pages=sum(1 for r in records if r.ocr_used),
    )
    return records


def is_scanned_pdf(pdf_path: Path, min_chars_per_page: int = 100) -> bool:
    """
    Quick check: returns True if the majority of pages appear to be scanned.
    Uses pdfminer for the check.
    """
    try:
        raw_pages = _extract_digital_text_pages(pdf_path)
    except Exception:
        return True  # If we can't read it, assume scanned
    if not raw_pages:
        return True
    scanned_count = sum(
        1 for _, text in raw_pages if len(text.strip()) < min_chars_per_page
    )
    return scanned_count >= len(raw_pages) / 2
