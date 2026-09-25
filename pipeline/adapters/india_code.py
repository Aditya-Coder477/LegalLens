"""
pipeline/adapters/india_code.py
================================
India Code (indiacode.nic.in) collection adapter.

Strategy (research-confirmed — DSpace REST API is disabled on this deployment):

  1. Paginate /browse?type=shorttitle&rpp=100&offset=N
     → Extracts Act handle IDs (/handle/123456789/{id})
     → robots.txt allows: /browse*, /handle/*, /bitstream/*
     → robots.txt disallows: /discover, /search-filter, /login, /statistics

  2. Fetch each Act page (/handle/123456789/{id})
     → Parse metadata: Act ID, title, act number, year, ministry, doc type
     → Find PDF bitstream link (/bitstream/123456789/{id}/{seq}/{file}.pdf)
     → Parse subordinate legislation tabs (Rules, Regulations, Notifications, etc.)

  3. Download PDFs to raw/india_code/{doc_type}/
     → 1 concurrent connection (Cloudflare/NIC WAF)
     → 2.5s + jitter delay between requests
     → Exponential backoff on 403/503

  4. Store metadata in catalogue

Authority: PRIMARY_OFFICIAL
"""

from __future__ import annotations

import re
import shutil
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
    CollectionMethod, DocumentMetadata, DocumentStatus, DocumentType,
    LegalDomain, SourceAuthority,
)
from pipeline.classification.classifier import classify_document

log = get_logger("india_code")

BASE_URL = "https://www.indiacode.nic.in"
SOURCE_NAME = "India Code"
SOURCE_ID_PREFIX = "india_code"


def _parse_act_handles(html: str, base_url: str) -> list[str]:
    """
    Extract act handle URLs from a browse page.
    Returns full URLs like https://www.indiacode.nic.in/handle/123456789/2187
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    handles = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.match(r"^/handle/123456789/\d+$", href):
            handles.append(base_url + href)
    return list(dict.fromkeys(handles))  # deduplicate preserving order


def _parse_act_metadata(html: str, act_url: str) -> dict:
    """
    Parse an act's landing page to extract metadata and bitstream URL.
    Returns a dict with keys: title, act_id, act_number, act_year, ministry,
    doc_type, pdf_url, bitstream_url, subordinate_links.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    data: dict = {
        "title": "",
        "act_id": None,
        "act_number": None,
        "act_year": None,
        "ministry": None,
        "department": None,
        "publication_date": None,
        "effective_date": None,
        "status": DocumentStatus.UNKNOWN.value,
        "bitstream_url": None,
        "subordinate_links": [],
    }

    # Title
    title_tag = soup.find("div", class_="act-title") or soup.find("h1")
    if title_tag:
        data["title"] = title_tag.get_text(strip=True)

    # Metadata table (DSpace style)
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True).lower()
            val = cells[1].get_text(strip=True)
            if "act id" in key or "actid" in key:
                data["act_id"] = val
            elif "act number" in key or "act no" in key:
                data["act_number"] = val
            elif "enactment year" in key or "year" in key:
                try:
                    data["act_year"] = int(re.search(r"\d{4}", val).group())
                except (AttributeError, ValueError):
                    pass
            elif "ministry" in key:
                data["ministry"] = val
            elif "department" in key:
                data["department"] = val
            elif "enforced" in key and "repealed" in val.lower():
                data["status"] = DocumentStatus.REPEALED.value
            elif "enactment date" in key or "date of enactment" in key:
                data["publication_date"] = val

    # Bitstream PDF link
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/bitstream/" in href and href.lower().endswith(".pdf"):
            if href.startswith("http"):
                data["bitstream_url"] = href
            else:
                data["bitstream_url"] = BASE_URL + href
            break

    # Subordinate legislation links (Rules, Regulations, Notifications tabs)
    sub_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        if any(doc_type in text for doc_type in ["rule", "regulation", "notification", "order", "circular", "ordinance"]):
            if "/handle/" in href or "/bitstream/" in href:
                full_url = href if href.startswith("http") else BASE_URL + href
                sub_links.append({"url": full_url, "text": text})
    data["subordinate_links"] = sub_links

    return data


def _infer_doc_type(title: str, text_hint: str = "") -> str:
    """Infer the document type from title or hint text."""
    combined = (title + " " + text_hint).lower()
    if "ordinance" in combined:
        return "ordinances"
    if "circular" in combined:
        return "circulars"
    if "notification" in combined:
        return "notifications"
    if "order" in combined and "court" not in combined:
        return "orders"
    if "regulation" in combined:
        return "regulations"
    if "rule" in combined:
        return "rules"
    return "acts"


async def collect(
    catalogue: Catalogue,
    raw_dir: str = "legal-data/raw/india_code",
    limit: Optional[int] = None,
    resume: bool = True,
    dry_run: bool = False,
) -> int:
    """
    Collect acts and subordinate legislation from India Code.

    Args:
        catalogue: The pipeline catalogue instance (already loaded).
        raw_dir: Root raw storage directory for India Code.
        limit: Max documents to collect (None = unlimited).
        resume: Skip already-downloaded documents.
        dry_run: Log what would be collected without downloading.

    Returns:
        Number of documents successfully collected.
    """
    cfg = get_config()
    base_url = cfg.india_code_base_url
    collected = 0

    log.info("Starting India Code collection", base_url=base_url, dry_run=dry_run, limit=limit)

    async with LegalLensClient(cfg) as client:
        offset = 0
        rpp = cfg.sources.india_code.browse_rpp

        while True:
            # Pagination: browse by short title
            browse_url = f"{base_url}/browse?type=shorttitle&rpp={rpp}&offset={offset}&order=ASC&sort_by=1"
            log.info("Fetching browse page", url=browse_url, offset=offset)

            try:
                resp = await client.get(browse_url)
                html = resp.text
            except RobotsBlockedError as exc:
                log.warning("Browse page blocked by robots.txt", url=browse_url, error=str(exc))
                break
            except DownloadError as exc:
                catalogue.mark_failed(
                    url=browse_url, source_name=SOURCE_NAME,
                    reason=str(exc), http_status=exc.http_status,
                )
                break

            act_handles = _parse_act_handles(html, base_url)
            if not act_handles:
                log.info("No more act handles found — browse complete", offset=offset)
                break

            for act_url in act_handles:
                if limit and collected >= limit:
                    log.info("Limit reached", limit=limit)
                    return collected

                if resume and catalogue.is_downloaded(act_url):
                    log.log_skipped(act_url, "already_downloaded")
                    continue

                if dry_run:
                    log.info("[DRY RUN] Would collect", url=act_url)
                    continue

                # Fetch act page
                try:
                    act_resp = await client.get(act_url)
                    act_meta = _parse_act_metadata(act_resp.text, act_url)
                except (DownloadError, RobotsBlockedError) as exc:
                    catalogue.mark_failed(
                        url=act_url, source_name=SOURCE_NAME,
                        reason=str(exc),
                        http_status=getattr(exc, "http_status", None),
                    )
                    continue

                if not act_meta.get("title"):
                    catalogue.mark_skipped(
                        url=act_url, source_id=SOURCE_ID_PREFIX,
                        reason="no_title_parsed"
                    )
                    continue

                doc_type_str = _infer_doc_type(act_meta["title"])
                dest_dir = Path(raw_dir) / doc_type_str
                dest_dir.mkdir(parents=True, exist_ok=True)

                # Download PDF bitstream if available
                local_path = None
                sha256 = None
                pdf_url = act_meta.get("bitstream_url")
                page_records = []
                extraction_status = "pending"
                first_page_text = ""
                ocr_used = False
                ocr_pages = 0

                if pdf_url:
                    safe_title = re.sub(r"[^\w\-.]", "_", act_meta["title"])[:80]
                    dest = dest_dir / f"{safe_title}.pdf"

                    try:
                        http_meta = await client.download_file(pdf_url, dest=dest)
                        # Validation
                        from pipeline.validation.validator import ArtifactValidator
                        val_res = ArtifactValidator.validate_file(dest, expected_format="pdf")
                        if not val_res.is_valid:
                            catalogue.mark_failed(
                                url=pdf_url, source_name=SOURCE_NAME,
                                reason=val_res.error_message or "Validation failed",
                                error_type=val_res.detected_type,
                            )
                            if dest.exists():
                                dest.unlink()
                            continue

                        sha256 = val_res.sha256
                        local_path = str(dest)
                        doc_id = f"{SOURCE_ID_PREFIX}_{sha256[:12]}"

                        # Extraction & OCR
                        from pipeline.extractors.dispatcher import extract
                        try:
                            page_records = extract(
                                file_path=dest,
                                document_id=doc_id,
                                source_url=pdf_url,
                                ocr_mode=cfg.ocr.mode,
                            )
                            for pr in page_records:
                                if pr.ocr_used:
                                    ocr_used = True
                                    ocr_pages += 1
                            if page_records:
                                first_page_text = page_records[0].text[:1000]

                            pages_dir = Path(cfg.storage.processed_dir) / "pages"
                            pages_dir.mkdir(parents=True, exist_ok=True)
                            with (pages_dir / f"{doc_id}.jsonl").open("w", encoding="utf-8") as pf:
                                for pr in page_records:
                                    pf.write(pr.model_dump_json() + "\n")
                            extraction_status = "success"
                        except Exception as exc:
                            log.warning("Extraction error", document_id=doc_id, error=str(exc))
                            extraction_status = "failed"

                    except (DownloadError, RobotsBlockedError) as exc:
                        catalogue.mark_failed(
                            url=pdf_url, source_name=SOURCE_NAME,
                            reason=str(exc),
                            http_status=getattr(exc, "http_status", None),
                            recommended_action="Download manually and use import_manual.py"
                        )
                        continue
                else:
                    doc_id = f"{SOURCE_ID_PREFIX}_{uuid4().hex[:12]}"

                source_inst_id = f"{doc_id}_{int(datetime.utcnow().timestamp())}"

                # Classify
                primary_domain, secondary, confidence, method = classify_document(
                    title=act_meta["title"],
                    ministry=act_meta.get("ministry") or "",
                    text_excerpt=first_page_text,
                )

                # Provenance
                from pipeline.provenance.provenance import ProvenanceRecord, ProvenanceRegistry
                prov_registry = ProvenanceRegistry(str(Path(cfg.storage.processed_dir) / "metadata" / "provenance.jsonl"))
                prov_records = []
                if page_records:
                    for pr in page_records:
                        prov_records.append(
                            ProvenanceRecord(
                                document_id=doc_id,
                                source_instance_id=source_inst_id,
                                source_id=doc_id,
                                source_name=SOURCE_NAME,
                                source_authority=SourceAuthority.PRIMARY_OFFICIAL,
                                source_url=pdf_url or act_url,
                                local_file=str(dest) if local_path else "",
                                sha256=sha256 or "",
                                page=pr.page,
                                section=pr.section,
                                heading=pr.heading,
                                extraction_method=pr.extraction_method,
                                ocr_used=pr.ocr_used,
                                ocr_confidence=pr.ocr_confidence,
                                legal_domain=primary_domain,
                            )
                        )
                    prov_registry.record_batch(prov_records)

                # Build metadata record
                doc_meta = DocumentMetadata(
                    source_id=doc_id,
                    document_id=doc_id,
                    source_instance_id=source_inst_id,
                    source_name=SOURCE_NAME,
                    source_type="legislation",
                    source_authority=SourceAuthority.PRIMARY_OFFICIAL,
                    legal_domain=primary_domain,
                    secondary_domains=secondary,
                    classification_confidence=confidence,
                    classification_method=method,
                    title=act_meta["title"],
                    document_type=DocumentType.ACT,
                    official_url=act_url,
                    download_url=pdf_url,
                    local_path=local_path,
                    file_format="pdf" if local_path else None,
                    ministry=act_meta.get("ministry"),
                    department=act_meta.get("department"),
                    act_number=act_meta.get("act_number"),
                    act_year=act_meta.get("act_year"),
                    act_id=act_meta.get("act_id"),
                    status=DocumentStatus(act_meta.get("status", "unknown")),
                    sha256=sha256,
                    file_size_bytes=Path(local_path).stat().st_size if local_path else None,
                    download_timestamp=datetime.utcnow(),
                    collection_method=CollectionMethod.BITSTREAM,
                    dspace_handle=act_url.replace(base_url, "").lstrip("/"),
                    validation_status="valid" if local_path else "pending",
                    extraction_status=extraction_status,
                    extraction_method="pdf_ocr" if ocr_used else ("pdf_text" if local_path else None),
                    ocr_used=ocr_used,
                    ocr_pages=ocr_pages,
                )
                catalogue.upsert_document(doc_meta)
                collected += 1

            # Next page
            offset += rpp

    log.info("India Code collection complete", collected=collected)
    return collected
