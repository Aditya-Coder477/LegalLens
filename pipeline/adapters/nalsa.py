"""
pipeline/adapters/nalsa.py
============================
NALSA (National Legal Services Authority) adapter.
100% feasible — no CAPTCHA, compliant robots.txt.

Collects from:
  - nalsa.gov.in/schemes-programmes
  - nalsa.gov.in/publications
  - nalsa.gov.in/acts-rules
  - nalsa.gov.in/statistics

Finds all /sites/default/files/*.pdf links and downloads them.

Authority: OFFICIAL_LEGAL_AID
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

log = get_logger("nalsa")

SOURCE_NAME = "National Legal Services Authority (NALSA)"
SOURCE_ID_PREFIX = "nalsa"
BASE_URL = "https://nalsa.gov.in"

INDEX_PATHS = [
    "/schemes-programmes",
    "/publications",
    "/acts-rules",
    "/statistics",
    "/loksabha-data",
]


def _extract_pdf_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """
    Extract (title, url) pairs for all PDF links on a NALSA page.
    Targets /sites/default/files/*.pdf and /writereaddata/*.pdf patterns.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.lower().endswith(".pdf"):
            continue
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = base_url + href
        else:
            full_url = base_url + "/" + href
        if full_url in seen:
            continue
        seen.add(full_url)
        title = a.get_text(strip=True) or _url_to_title(href)
        links.append((title, full_url))
    return links


def _url_to_title(url: str) -> str:
    """Derive a human-readable title from a URL filename."""
    name = url.split("/")[-1].replace(".pdf", "").replace("_", " ").replace("-", " ")
    return name.strip().title()


async def collect(
    catalogue: Catalogue,
    raw_dir: str = "legal-data/raw/nalsa",
    limit: Optional[int] = None,
    resume: bool = True,
    dry_run: bool = False,
) -> int:
    cfg = get_config()
    source_cfg = cfg.sources.nalsa
    base_url = source_cfg.base_url or BASE_URL
    index_paths = source_cfg.index_paths or INDEX_PATHS
    log.info("Starting NALSA collection", base_url=base_url, dry_run=dry_run)
    collected = 0
    all_pdf_links: list[tuple[str, str]] = []

    async with LegalLensClient(cfg) as client:
        # Discover all PDF links from configured index pages
        for index_path in index_paths:
            index_url = base_url + index_path
            try:
                resp = await client.get(index_url)
                links = _extract_pdf_links(resp.text, base_url)
                log.info("Found PDF links", url=index_url, count=len(links))
                all_pdf_links.extend(links)
            except (DownloadError, RobotsBlockedError) as exc:
                catalogue.mark_failed(
                    url=index_url, source_name=SOURCE_NAME,
                    reason=str(exc), http_status=getattr(exc, "http_status", None),
                )

        # Deduplicate
        seen_urls = set()
        unique_links = []
        for title, url in all_pdf_links:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_links.append((title, url))

        log.info("Total unique PDFs found", count=len(unique_links))

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
                http_meta = await client.download_file(pdf_url, dest=dest)
            except (DownloadError, RobotsBlockedError) as exc:
                catalogue.mark_failed(
                    url=pdf_url, source_name=SOURCE_NAME,
                    reason=str(exc), http_status=getattr(exc, "http_status", None),
                )
                continue

            # 1. Artifact Validation
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

            # 2. Text Extraction & OCR
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

                # Persist extracted pages
                pages_file = pages_dir / f"{doc_id}.jsonl"
                with pages_file.open("w", encoding="utf-8") as pf:
                    for pr in page_records:
                        pf.write(pr.model_dump_json() + "\n")
                extraction_status = "success"
            except Exception as exc:
                log.warning("Extraction error", document_id=doc_id, error=str(exc))
                extraction_status = "failed"

            # 3. Post-Extraction Classification using Title + Text Excerpt
            primary, secondary, confidence, method = classify_document(
                title=title,
                ministry="NALSA",
                text_excerpt=first_page_text,
            )

            # 4. Provenance Recording
            prov_records = []
            if page_records:
                for pr in page_records:
                    prov_records.append(
                        ProvenanceRecord(
                            document_id=doc_id,
                            source_instance_id=source_inst_id,
                            source_id=doc_id,
                            source_name=SOURCE_NAME,
                            source_authority=SourceAuthority.OFFICIAL_LEGAL_AID,
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
            else:
                from pipeline.core.metadata import ExtractionMethod
                prov_records.append(
                    ProvenanceRecord(
                        document_id=doc_id,
                        source_instance_id=source_inst_id,
                        source_id=doc_id,
                        source_name=SOURCE_NAME,
                        source_authority=SourceAuthority.OFFICIAL_LEGAL_AID,
                        source_url=pdf_url,
                        local_file=str(dest),
                        sha256=sha256,
                        extraction_method=ExtractionMethod.PDF_TEXT,
                        legal_domain=primary,
                    )
                )
            prov_registry.record_batch(prov_records)

            # 5. Canonical Metadata & Catalogue
            doc_meta = DocumentMetadata(
                source_id=doc_id,
                document_id=doc_id,
                source_instance_id=source_inst_id,
                source_name=SOURCE_NAME,
                source_type="legal_aid",
                source_authority=SourceAuthority.OFFICIAL_LEGAL_AID,
                legal_domain=primary,
                secondary_domains=secondary,
                classification_confidence=confidence,
                classification_method=method,
                title=title,
                document_type=DocumentType.REPORT,
                official_url=pdf_url,
                local_path=str(dest),
                file_format="pdf",
                ministry="National Legal Services Authority",
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

    log.info("NALSA collection complete", collected=collected)
    return collected
