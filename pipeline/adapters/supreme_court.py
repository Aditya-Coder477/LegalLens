"""
pipeline/adapters/supreme_court.py
=====================================
Supreme Court of India (sci.gov.in) adapter.
STATIC DOCUMENTS ONLY — CAPTCHA-free paths only.

What this adapter collects:
  - Circulars, notifications, practice directions
  - Annual reports
  - Supreme Court Rules 2013
  - Administrative orders and office memoranda
  - Cause lists (static PDFs where accessible)
  - Roster / bench allocation lists

What this adapter does NOT attempt:
  - Judgment search on main.sci.gov.in (requires CAPTCHA)
  - Case status search (requires CAPTCHA)
  - Anything on scr.sci.gov.in search forms (requires CAPTCHA)

Blocked paths documented in MANUAL_COLLECTION_TODO.md with instructions.

Authority: OFFICIAL_COURT
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pipeline.core.catalogue import Catalogue
from pipeline.core.config import get_config
from pipeline.core.hasher import sha256_file
from pipeline.core.http_client import LegalLensClient, DownloadError, RobotsBlockedError
from pipeline.core.logger import get_logger
from pipeline.core.metadata import (
    CollectionMethod, DocumentMetadata, DocumentType,
    LegalDomain, SourceAuthority,
)
from pipeline.classification.classifier import classify_document

log = get_logger("supreme_court")

SOURCE_NAME = "Supreme Court of India"
SOURCE_ID_PREFIX = "supreme_court"
BASE_URL = "https://www.sci.gov.in"

# CAPTCHA-free static paths (confirmed by research)
STATIC_INDEX_PATHS = [
    "/pdf/",                # Circulars, notifications
    "/wp-content/uploads/", # Reports, documents
]

# Static entry-point pages to crawl for PDF links
STATIC_ENTRY_PAGES = [
    "/home/index.php/rules",
    "/home/index.php/practice-direction",
    "/home/index.php/annual-reports",
    "/home/index.php/notifications",
    "/home/index.php/practice-direction/circulars",
    "/home/index.php/cause-list",
]

MANUAL_TODO_ENTRY = """
## Supreme Court of India — Judgment Search (Manual Collection Required)

**Source:** main.sci.gov.in, scr.sci.gov.in (eSCR — Electronic Supreme Court Reports)  
**Reason not automated:** Search forms on main.sci.gov.in and scr.sci.gov.in require CAPTCHA.  
**Status:** MANUAL IMPORT ONLY

### What the automated adapter collects
- Circulars, notifications, practice directions (static PDFs on sci.gov.in/pdf/)
- Annual reports, Supreme Court Rules
- Administrative documents

### What requires manual collection
- Full-text judgments (all years, all benches)
- Daily orders
- Cause list archives (dynamic search)

### Recommended approach for judgment collection
1. Visit https://scr.sci.gov.in/ and search/download judgments manually
2. Also consider: https://judgments.ecourts.gov.in/ for combined court search
3. Import downloaded PDFs using:

```bash
python import_manual.py path/to/judgment.pdf \\
  --source supreme_court \\
  --doc-type judgment \\
  --domain "Constitutional Law" \\
  --title "Case Title" \\
  --url "https://sci.gov.in/..." \\
  --date YYYY-MM-DD
```
"""


def _extract_pdf_links(html: str, base_url: str, year_from: int = 2015) -> list[tuple[str, str]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    links = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.lower().endswith(".pdf"):
            continue
        # Check year filter: if href contains a year, check it
        year_match = re.search(r"20\d{2}", href)
        if year_match:
            doc_year = int(year_match.group())
            if doc_year < year_from:
                continue
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = base_url + href
        else:
            continue
        if full_url in seen:
            continue
        seen.add(full_url)
        title = a.get_text(strip=True) or full_url.split("/")[-1].replace(".pdf", "").replace("_", " ")
        links.append((title.strip(), full_url))
    return links


async def collect(
    catalogue: Catalogue,
    raw_dir: str = "legal-data/raw/supreme_court",
    limit: Optional[int] = None,
    resume: bool = True,
    dry_run: bool = False,
    todo_path: str = "MANUAL_COLLECTION_TODO.md",
) -> int:
    cfg = get_config()
    source_cfg = cfg.sources.supreme_court
    base_url = source_cfg.base_url or BASE_URL
    year_from = source_cfg.year_from or 2015
    index_paths = source_cfg.index_paths or STATIC_ENTRY_PAGES
    log.info(
        "Starting Supreme Court static collection",
        base_url=base_url, year_from=year_from, dry_run=dry_run
    )
    collected = 0
    all_links: list[tuple[str, str]] = []

    # Add judgment search gap to manual TODO
    _update_todo(todo_path)

    async with LegalLensClient(cfg) as client:
        for entry_path in index_paths:
            entry_url = base_url + entry_path
            try:
                resp = await client.get(entry_url)
                links = _extract_pdf_links(resp.text, base_url, year_from)
                log.info("Found static PDF links", url=entry_url, count=len(links))
                all_links.extend(links)
            except (DownloadError, RobotsBlockedError) as exc:
                catalogue.mark_failed(
                    url=entry_url, source_name=SOURCE_NAME,
                    reason=str(exc), http_status=getattr(exc, "http_status", None),
                )

        seen_urls: set[str] = set()
        unique_links = []
        for t, u in all_links:
            if u not in seen_urls:
                seen_urls.add(u)
                unique_links.append((t, u))
        log.info("Total unique SCI static documents", count=len(unique_links))

        from pipeline.extractors.dispatcher import extract
        from pipeline.provenance.provenance import ProvenanceRecord, ProvenanceRegistry
        from pipeline.validation.validator import ArtifactValidator

        provenance_path = Path(cfg.storage.processed_dir) / "metadata" / "provenance.jsonl"
        prov_registry = ProvenanceRegistry(str(provenance_path))
        pages_dir = Path(cfg.storage.processed_dir) / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        for title, pdf_url in unique_links:
            if limit and collected >= limit:
                break
            if resume and catalogue.is_downloaded(pdf_url):
                log.log_skipped(pdf_url, "already_downloaded")
                continue
            if dry_run:
                log.info("[DRY RUN] Would collect", title=title, url=pdf_url)
                continue

            dest_dir = Path(raw_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)
            clean_name = re.sub(r"[^\w\-.]", "_", pdf_url.split("/")[-1])[:120]
            if not clean_name.lower().endswith(".pdf"):
                clean_name += ".pdf"
            dest = dest_dir / clean_name

            try:
                await client.download_file(pdf_url, dest=dest)
            except (DownloadError, RobotsBlockedError) as exc:
                catalogue.mark_failed(
                    url=pdf_url, source_name=SOURCE_NAME,
                    reason=str(exc), http_status=getattr(exc, "http_status", None),
                )
                continue

            # 1. Validation
            val_res = ArtifactValidator.validate_file(dest, expected_format="pdf")
            if not val_res.is_valid:
                catalogue.mark_failed(
                    url=pdf_url,
                    source_name=SOURCE_NAME,
                    reason=val_res.error_message or "Artifact validation failed",
                    error_type=val_res.detected_type,
                )
                if dest.exists():
                    dest.unlink()
                continue

            sha256 = val_res.sha256
            doc_id = f"{SOURCE_ID_PREFIX}_{sha256[:12]}"
            source_inst_id = f"{doc_id}_{int(datetime.utcnow().timestamp())}"

            # 2. Text extraction & OCR
            ocr_pages_count = 0
            ocr_actually_used = False
            first_page_text = ""
            page_records = []
            try:
                page_records = extract(
                    file_path=dest,
                    document_id=doc_id,
                    source_url=pdf_url,
                    ocr_mode=cfg.ocr.mode,
                )
                for pr in page_records:
                    if pr.ocr_used:
                        ocr_actually_used = True
                        ocr_pages_count += 1
                if page_records:
                    first_page_text = page_records[0].text[:1000]

                pages_file = pages_dir / f"{doc_id}.jsonl"
                with pages_file.open("w", encoding="utf-8") as pf:
                    for pr in page_records:
                        pf.write(pr.model_dump_json() + "\n")
                extraction_status = "success"
            except Exception as exc:
                log.warning("Extraction error", document_id=doc_id, error=str(exc))
                extraction_status = "failed"

            # 3. Post-extraction classification
            primary, secondary, confidence, method = classify_document(
                title=title,
                text_excerpt=first_page_text,
            )

            # 4. Provenance
            prov_records = []
            if page_records:
                for pr in page_records:
                    prov_records.append(
                        ProvenanceRecord(
                            document_id=doc_id,
                            source_instance_id=source_inst_id,
                            source_id=doc_id,
                            source_name=SOURCE_NAME,
                            source_authority=SourceAuthority.OFFICIAL_COURT,
                            source_url=pdf_url,
                            local_file=str(dest),
                            sha256=sha256,
                            page=pr.page,
                            section=pr.section,
                            heading=pr.heading,
                            extraction_method=pr.extraction_method,
                            ocr_used=pr.ocr_used,
                            ocr_confidence=pr.ocr_confidence,
                            legal_domain=primary,
                        )
                    )
            prov_registry.record_batch(prov_records)

            # 5. Metadata & Catalogue
            doc_meta = DocumentMetadata(
                source_id=doc_id,
                document_id=doc_id,
                source_instance_id=source_inst_id,
                source_name=SOURCE_NAME,
                source_type="court_document",
                source_authority=SourceAuthority.OFFICIAL_COURT,
                legal_domain=primary,
                secondary_domains=secondary,
                classification_confidence=confidence,
                classification_method=method,
                title=title,
                document_type=DocumentType.OTHER,
                official_url=pdf_url,
                local_path=str(dest),
                file_format="pdf",
                sha256=sha256,
                file_size_bytes=dest.stat().st_size,
                download_timestamp=datetime.utcnow(),
                collection_method=CollectionMethod.DIRECT_DOWNLOAD,
                validation_status="valid",
                extraction_status=extraction_status,
                extraction_method="pdf_ocr" if ocr_actually_used else "pdf_text",
                ocr_used=ocr_actually_used,
                ocr_pages=ocr_pages_count,
            )
            catalogue.upsert_document(doc_meta)
            log.log_download_success(pdf_url, str(dest), sha256, dest.stat().st_size)
            collected += 1

    log.info("Supreme Court static collection complete", collected=collected)
    return collected


def _update_todo(todo_path: str) -> None:
    path = Path(todo_path)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if "Supreme Court of India — Judgment Search" in existing:
            return
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n{MANUAL_TODO_ENTRY}\n")
    log.info("Updated MANUAL_COLLECTION_TODO.md with SCI judgment instructions")
