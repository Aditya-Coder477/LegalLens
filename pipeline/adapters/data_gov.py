"""
pipeline/adapters/data_gov.py
===============================
data.gov.in Open Government Data Platform API adapter.

Uses the official REST API at api.data.gov.in (no scraping required).
API key required (free registration at data.gov.in).

API endpoint:
  GET https://api.data.gov.in/resource/{resource_id}?api-key={KEY}&format={json|csv}&offset=0&limit=100

Discovery:
  GET https://api.data.gov.in/catalog/all?api-key={KEY}&format=json&filters[sector]={sector}

Rate limits (free tier): 1,000 calls/day
Counter persisted to logs/.daily_call_count to avoid exceeding limit.

Authority: OFFICIAL_GOVERNMENT
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pipeline.core.catalogue import Catalogue
from pipeline.core.config import get_config
from pipeline.core.hasher import sha256_text
from pipeline.core.http_client import LegalLensClient, DownloadError, redact_secrets_from_url
from pipeline.core.logger import get_logger
from pipeline.core.metadata import (
    CollectionMethod, DocumentMetadata, DocumentType,
    LegalDomain, SourceAuthority, ExtractionMethod, PageRecord,
)
from pipeline.classification.classifier import classify_document
from pipeline.provenance.provenance import ProvenanceRecord, ProvenanceRegistry
from pipeline.validation.validator import ArtifactValidator

log = get_logger("data_gov")

SOURCE_NAME = "Open Government Data Platform India"
SOURCE_ID_PREFIX = "data_gov"
API_BASE = "https://api.data.gov.in"

# Legal/judiciary topics to search
LEGAL_TOPICS = [
    "judiciary", "courts", "legal services", "justice", "labour",
    "consumer affairs", "police", "crime", "legal aid", "lok adalat",
    "law and justice", "criminal justice", "prison", "tele-law",
]


def _load_call_counter(log_dir: str) -> int:
    path = Path(log_dir) / ".daily_call_count"
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text())
        if data.get("date") == date.today().isoformat():
            return int(data.get("count", 0))
    except Exception:
        pass
    return 0


def _save_call_counter(log_dir: str, count: int) -> None:
    path = Path(log_dir) / ".daily_call_count"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"date": date.today().isoformat(), "count": count}))


async def collect(
    catalogue: Catalogue,
    raw_dir: str = "legal-data/raw/data_gov",
    limit: Optional[int] = None,
    resume: bool = True,
    dry_run: bool = False,
    log_dir: str = "legal-data/logs",
) -> int:
    """
    Collect legal/judiciary datasets from data.gov.in using the official API.

    Returns:
        Number of datasets successfully collected.
    """
    cfg = get_config()
    api_key = cfg.data_gov_api_key
    daily_limit = cfg.sources.data_gov.daily_call_limit
    api_base = cfg.data_gov_api_base

    if not api_key:
        log.warning(
            "data.gov.in API key not configured — skipping source",
            note="Set DATA_GOV_API_KEY in .env. Register at: https://data.gov.in/user/register",
        )
        catalogue.mark_skipped(
            url=api_base,
            source_id=SOURCE_ID_PREFIX,
            reason="no_api_key",
            note="Set DATA_GOV_API_KEY in .env to enable this source.",
        )
        return 0

    call_count = _load_call_counter(log_dir)
    if call_count >= daily_limit:
        log.warning(
            "Daily API call limit reached — skipping data.gov.in",
            daily_limit=daily_limit,
            calls_made=call_count,
        )
        return 0

    log.info("Starting data.gov.in collection", api_base=api_base, dry_run=dry_run)
    collected = 0
    topics = cfg.sources.data_gov.topics or LEGAL_TOPICS

    provenance_path = Path(cfg.storage.processed_dir) / "metadata" / "provenance.jsonl"
    prov_registry = ProvenanceRegistry(str(provenance_path))

    async with LegalLensClient(cfg) as client:
        for topic in topics:
            if limit and collected >= limit:
                break
            if call_count >= daily_limit:
                log.warning("Daily call limit reached mid-collection", calls_made=call_count)
                break

            # Search catalog by topic/keyword
            search_url = (
                f"{api_base}/catalog/all"
                f"?api-key={api_key}&format=json&limit=20&offset=0"
                f"&filters[keyword]={topic.replace(' ', '+')}"
            )
            try:
                resp = await client.get(search_url, check_robots=False)
                call_count += 1
                _save_call_counter(log_dir, call_count)
            except DownloadError as exc:
                catalogue.mark_failed(
                    url=redact_secrets_from_url(search_url),
                    source_name=SOURCE_NAME,
                    reason=redact_secrets_from_url(str(exc)),
                    http_status=exc.http_status,
                )
                continue

            try:
                data = resp.json()
            except Exception:
                log.warning("Could not parse JSON response", url=redact_secrets_from_url(search_url))
                continue

            records = data.get("records", []) or data.get("data", [])
            if not records:
                log.info("No datasets found for topic", topic=topic)
                continue

            for record in records:
                if limit and collected >= limit:
                    break
                if call_count >= daily_limit:
                    break

                resource_id = record.get("resource_id") or record.get("id", "")
                title = record.get("title") or record.get("name", f"Dataset-{resource_id}")
                official_url = f"https://data.gov.in/resource/{resource_id}"
                download_url = f"{api_base}/resource/{resource_id}?api-key={api_key}&format=csv"
                clean_download_url = redact_secrets_from_url(download_url)

                if resume and catalogue.is_downloaded(official_url):
                    log.log_skipped(official_url, "already_downloaded")
                    continue

                if dry_run:
                    log.info("[DRY RUN] Would collect dataset", title=title, url=official_url)
                    continue

                # Download dataset as CSV
                dest_dir = Path(raw_dir)
                dest_dir.mkdir(parents=True, exist_ok=True)
                safe_title = re.sub(r"[^\w\-]", "_", title)[:80]
                dest = dest_dir / f"{resource_id}_{safe_title}.csv"

                try:
                    resp2 = await client.get(download_url, check_robots=False)
                    call_count += 1
                    _save_call_counter(log_dir, call_count)
                except DownloadError as exc:
                    catalogue.mark_failed(
                        url=clean_download_url,
                        source_name=SOURCE_NAME,
                        reason=redact_secrets_from_url(str(exc)),
                        http_status=exc.http_status,
                    )
                    continue

                # Validate CSV
                val_res = ArtifactValidator.validate_bytes(resp2.content, "csv")
                if not val_res.is_valid:
                    catalogue.mark_failed(
                        url=clean_download_url,
                        source_name=SOURCE_NAME,
                        reason=val_res.error_message or "Artifact validation failed",
                        error_type=val_res.detected_type,
                    )
                    continue

                dest.write_bytes(resp2.content)
                sha256 = val_res.sha256
                doc_id = f"{SOURCE_ID_PREFIX}_{sha256[:12]}"
                source_inst_id = f"{doc_id}_{int(datetime.utcnow().timestamp())}"

                log.log_download_success(
                    url=clean_download_url,
                    local_path=str(dest),
                    sha256=sha256,
                    size_bytes=dest.stat().st_size,
                )

                primary_domain, secondary, confidence, method = classify_document(title=title)

                # Provenance
                prov = ProvenanceRecord(
                    document_id=doc_id,
                    source_instance_id=source_inst_id,
                    source_id=doc_id,
                    source_name=SOURCE_NAME,
                    source_authority=SourceAuthority.OFFICIAL_GOVERNMENT,
                    source_url=clean_download_url,
                    local_file=str(dest),
                    sha256=sha256,
                    page=1,
                    extraction_method=ExtractionMethod.NATIVE_TEXT,
                    legal_domain=primary_domain,
                )
                prov_registry.record_provenance(prov)

                doc_meta = DocumentMetadata(
                    document_id=doc_id,
                    source_instance_id=source_inst_id,
                    source_id=doc_id,
                    source_name=SOURCE_NAME,
                    source_type="dataset",
                    source_authority=SourceAuthority.OFFICIAL_GOVERNMENT,
                    legal_domain=primary_domain,
                    secondary_domains=secondary,
                    classification_confidence=confidence,
                    classification_method=method,
                    title=title,
                    document_type=DocumentType.DATASET,
                    official_url=official_url,
                    download_url=clean_download_url,
                    local_path=str(dest),
                    file_format="csv",
                    sha256=sha256,
                    download_timestamp=datetime.utcnow(),
                    collection_method=CollectionMethod.API,
                    validation_status="valid",
                    extraction_status="success",
                    extraction_method=ExtractionMethod.NATIVE_TEXT,
                )
                catalogue.upsert_document(doc_meta)
                collected += 1

    _save_call_counter(log_dir, call_count)
    log.info("data.gov.in collection complete", collected=collected, api_calls=call_count)
    return collected
