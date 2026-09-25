"""
pipeline/adapters/legislative_dept.py
========================================
Legislative Department (legislative.gov.in) adapter.
100% feasible — no CAPTCHA, compliant robots.txt.

Collects from:
  - legislative.gov.in/constitution-of-india/
  - legislative.gov.in/central-acts/
  - legislative.gov.in/ordinances/
  - legislative.gov.in/amendment-acts/

Finds all /sites/default/files/*.pdf links and downloads them.

Authority: PRIMARY_OFFICIAL
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

log = get_logger("legislative_dept")

SOURCE_NAME = "Legislative Department, Ministry of Law and Justice"
SOURCE_ID_PREFIX = "legislative_dept"
BASE_URL = "https://legislative.gov.in"

INDEX_PATHS = [
    "/constitution-of-india/",
    "/central-acts/",
    "/ordinances/",
    "/amendment-acts/",
]

_DOC_TYPE_MAP = {
    "constitution": DocumentType.CONSTITUTION,
    "ordinance": DocumentType.ORDINANCE,
    "amendment": DocumentType.AMENDMENT,
    "central-act": DocumentType.ACT,
    "act": DocumentType.ACT,
}


def _extract_pdf_links(html: str, base_url: str) -> list[tuple[str, str]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not (href.lower().endswith(".pdf") or "/sites/default/files/" in href.lower()):
            if not href.lower().endswith(".pdf"):
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


def _infer_doc_type(url: str, title: str) -> DocumentType:
    combined = (url + " " + title).lower()
    for key, dtype in _DOC_TYPE_MAP.items():
        if key in combined:
            return dtype
    return DocumentType.ACT


async def collect(
    catalogue: Catalogue,
    raw_dir: str = "legal-data/raw/legislative_department",
    limit: Optional[int] = None,
    resume: bool = True,
    dry_run: bool = False,
) -> int:
    cfg = get_config()
    source_cfg = cfg.sources.legislative_dept
    base_url = source_cfg.base_url or BASE_URL
    index_paths = source_cfg.index_paths or INDEX_PATHS
    log.info("Starting Legislative Department collection", base_url=base_url, dry_run=dry_run)
    collected = 0
    all_links: list[tuple[str, str]] = []

    async with LegalLensClient(cfg) as client:
        for path in index_paths:
            index_url = base_url + path
            try:
                resp = await client.get(index_url)
                links = _extract_pdf_links(resp.text, base_url)
                log.info("Found PDF links", url=index_url, count=len(links))
                all_links.extend(links)
            except (DownloadError, RobotsBlockedError) as exc:
                catalogue.mark_failed(
                    url=index_url, source_name=SOURCE_NAME,
                    reason=str(exc), http_status=getattr(exc, "http_status", None),
                )

        # Deduplicate
        seen_urls: set[str] = set()
        unique_links = []
        for t, u in all_links:
            if u not in seen_urls:
                seen_urls.add(u)
                unique_links.append((t, u))

        log.info("Total unique documents found", count=len(unique_links))

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

                pages_file = pages_dir / f"{doc_id}.jsonl"
                with pages_file.open("w", encoding="utf-8") as pf:
                    for pr in page_records:
                        pf.write(pr.model_dump_json() + "\n")
                extraction_status = "success"
            except Exception as exc:
                log.warning("Extraction error", document_id=doc_id, error=str(exc))
                extraction_status = "failed"

            doc_type = _infer_doc_type(pdf_url)
            primary, secondary, confidence, method = classify_document(
                title=title,
                ministry="Ministry of Law and Justice",
                text_excerpt=first_page_text,
            )

            # 3. Provenance
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

            # 4. Metadata & Catalogue
            doc_meta = DocumentMetadata(
                source_id=doc_id,
                document_id=doc_id,
                source_instance_id=source_inst_id,
                source_name=SOURCE_NAME,
                source_type="legislation",
                source_authority=SourceAuthority.PRIMARY_OFFICIAL,
                legal_domain=primary,
                secondary_domains=secondary,
                classification_confidence=confidence,
                classification_method=method,
                title=title,
                document_type=doc_type,
                official_url=pdf_url,
                local_path=str(dest),
                file_format="pdf",
                ministry="Ministry of Law and Justice",
                department="Legislative Department",
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

    log.info("Legislative Department collection complete", collected=collected)
    return collected
