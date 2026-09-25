"""
pipeline/extractors/html_extractor.py
======================================
HTML text extraction using BeautifulSoup + lxml.

Strips: navigation, headers, footers, sidebars, scripts, styles.
Preserves: heading hierarchy (h1–h6), paragraph structure, ordered/unordered lists.
Output: List[PageRecord] — a single "page" for an HTML document, or one page
per logical section if headings are clearly delimited.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from pipeline.core.metadata import ExtractionMethod, LegalDomain, PageRecord
from pipeline.core.logger import get_logger

log = get_logger("html_extractor")

# Tags whose content should be entirely stripped
_STRIP_TAGS = {
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "button", "input", "select", "textarea",
    "iframe", "embed", "object", "img", "svg", "canvas",
    "advertisement", "menu", "breadcrumb",
}

# Tags that suggest navigation/boilerplate by class/id
_STRIP_CLASS_PATTERNS = re.compile(
    r"(nav|menu|header|footer|sidebar|breadcrumb|advertisement|cookie|"
    r"social|share|related|comment|widget|banner|popup|modal|overlay)",
    re.IGNORECASE,
)


def _get_bs4():
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup
    except ImportError as e:
        raise ImportError(
            "beautifulsoup4 is required. Install: pip install beautifulsoup4 lxml"
        ) from e


def _should_strip_element(tag) -> bool:
    """Return True if an element is navigation/boilerplate and should be removed."""
    if tag.name in _STRIP_TAGS:
        return True
    for attr in ("class", "id", "role"):
        val = tag.get(attr, "")
        if isinstance(val, list):
            val = " ".join(val)
        if val and _STRIP_CLASS_PATTERNS.search(val):
            return True
    return False


def _clean_html(soup) -> None:
    """In-place removal of boilerplate elements."""
    for tag in soup.find_all(True):
        if _should_strip_element(tag):
            tag.decompose()


def _extract_structure(soup) -> list[dict]:
    """
    Walk the cleaned soup and extract a list of {heading, text} sections.
    Falls back to a single flat text block if no headings are found.
    """
    sections: list[dict] = []
    current_heading: Optional[str] = None
    current_text_parts: list[str] = []

    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "dt", "dd"]):
        if el.name in HEADING_TAGS:
            # Save previous section
            if current_text_parts:
                sections.append({
                    "heading": current_heading,
                    "text": "\n".join(current_text_parts).strip(),
                })
                current_text_parts = []
            current_heading = el.get_text(separator=" ", strip=True)[:200]
        else:
            text = el.get_text(separator=" ", strip=True)
            if text:
                current_text_parts.append(text)

    # Final section
    if current_text_parts:
        sections.append({
            "heading": current_heading,
            "text": "\n".join(current_text_parts).strip(),
        })

    return sections


def extract_html_file(
    html_path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str = LegalDomain.UNCLASSIFIED.value,
) -> list[PageRecord]:
    """Extract text from an HTML file."""
    content = html_path.read_text(encoding="utf-8", errors="replace")
    return extract_html_string(
        content, document_id=document_id,
        source_url=source_url, legal_domain=legal_domain
    )


def extract_html_string(
    html: str,
    document_id: str,
    source_url: str,
    legal_domain: str = LegalDomain.UNCLASSIFIED.value,
) -> list[PageRecord]:
    """
    Extract text from an HTML string.

    Returns:
        List of PageRecord objects (one per heading-delimited section).
    """
    BeautifulSoup = _get_bs4()

    soup = BeautifulSoup(html, "lxml")
    _clean_html(soup)
    sections = _extract_structure(soup)

    if not sections:
        # Fallback: extract all text as a single page
        text = soup.get_text(separator="\n", strip=True)
        if not text.strip():
            log.warning("HTML extraction yielded empty text", document_id=document_id)
            return []
        sections = [{"heading": None, "text": text}]

    records: list[PageRecord] = []
    for i, sec in enumerate(sections, start=1):
        records.append(
            PageRecord(
                document_id=document_id,
                page=i,
                heading=sec.get("heading"),
                text=sec["text"],
                source_url=source_url,
                legal_domain=legal_domain,
                extraction_method=ExtractionMethod.HTML,
            )
        )

    log.info(
        "HTML extraction complete",
        document_id=document_id,
        sections=len(records),
    )
    return records
