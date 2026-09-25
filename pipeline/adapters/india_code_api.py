"""
pipeline/adapters/india_code_api.py
=====================================
indiacode.ecourtsindia.com API adapter — supplementary section-level source.

This is a SECONDARY_COMMUNITY tier source. If content from this API disagrees
with India Code (PRIMARY_OFFICIAL), a discrepancy is flagged for human review.
The India Code adapter's content takes precedence.

OpenAPI 3.0 spec: https://indiacode.ecourtsindia.com/api/v1/openapi.json
No authentication required. CORS enabled.

Endpoints used:
  GET /api/v1/search?q={query}     → search acts by keyword
  GET /api/v1/{act_code}/section/{section_number} → section text (JSON + Markdown)

Authority: SECONDARY_COMMUNITY
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pipeline.core.catalogue import Catalogue
from pipeline.core.config import get_config
from pipeline.core.hasher import sha256_text
from pipeline.core.http_client import LegalLensClient, DownloadError
from pipeline.core.logger import get_logger
from pipeline.core.metadata import (
    CollectionMethod, DocumentMetadata, DocumentType,
    LegalDomain, SourceAuthority, ExtractionMethod, PageRecord,
)
from pipeline.classification.classifier import classify_document
from pipeline.provenance.provenance import ProvenanceRecord, ProvenanceRegistry
from pipeline.validation.validator import ArtifactValidator

log = get_logger("india_code_api")

SOURCE_NAME = "India Code (indiacode.ecourtsindia.com API)"
SOURCE_ID_PREFIX = "india_code_api"
API_BASE = "https://indiacode.ecourtsindia.com/api"

# Common acts to seed section collection
SEED_QUERIES = [
    "Indian Contract Act",
    "Indian Penal Code",
    "Bharatiya Nyaya Sanhita",
    "Code of Criminal Procedure",
    "Information Technology Act",
    "Digital Personal Data Protection",
    "Companies Act",
    "Consumer Protection Act",
    "Transfer of Property Act",
    "Hindu Marriage Act",
]


async def collect(
    catalogue: Catalogue,
    raw_dir: str = "legal-data/raw/india_code/sections",
    limit: Optional[int] = None,
    resume: bool = True,
    dry_run: bool = False,
) -> int:
    cfg = get_config()

    if not cfg.sources.india_code.use_ecourtsindia_api:
        log.info("india_code_api disabled in config (use_ecourtsindia_api=false)")
        return 0

    api_base = cfg.india_code_api_base
    log.info("Starting indiacode.ecourtsindia.com API collection", api_base=api_base)
    collected = 0

    provenance_path = Path(cfg.storage.processed_dir) / "metadata" / "provenance.jsonl"
    prov_registry = ProvenanceRegistry(str(provenance_path))

    async with LegalLensClient(cfg) as client:
        for query in SEED_QUERIES:
            if limit and collected >= limit:
                break

            search_url = f"{api_base}/v1/search?q={query.replace(' ', '+')}"
            try:
                resp = await client.get(search_url, check_robots=False)
                results = resp.json()
            except (DownloadError, Exception) as exc:
                catalogue.mark_failed(
                    url=search_url, source_name=SOURCE_NAME,
                    reason=str(exc),
                )
                continue

            acts = results if isinstance(results, list) else results.get("acts", []) or results.get("results", [])

            for act in acts[:5]:  # limit per query
                if limit and collected >= limit:
                    break

                act_code = act.get("code") or act.get("act_code") or act.get("id", "")
                title = act.get("title") or act.get("name") or act.get("short_title", "")
                if not act_code or not title:
                    continue

                official_url = f"{api_base}/v1/{act_code}"
                if resume and catalogue.is_downloaded(official_url):
                    log.log_skipped(official_url, "already_downloaded")
                    continue

                if dry_run:
                    log.info("[DRY RUN] Would collect act", title=title, act_code=act_code)
                    continue

                # Fetch full act data
                try:
                    act_resp = await client.get(official_url, check_robots=False)
                    act_data = act_resp.json()
                except (DownloadError, Exception) as exc:
                    catalogue.mark_failed(
                        url=official_url, source_name=SOURCE_NAME,
                        reason=str(exc),
                    )
                    continue

                json_bytes = json.dumps(act_data, indent=2, ensure_ascii=False).encode("utf-8")
                val_res = ArtifactValidator.validate_bytes(json_bytes, "json")
                if not val_res.is_valid:
                    catalogue.mark_failed(
                        url=official_url,
                        source_name=SOURCE_NAME,
                        reason=val_res.error_message or "Artifact validation failed",
                        error_type=val_res.detected_type,
                    )
                    continue

                # Store raw JSON
                dest_dir = Path(raw_dir)
                dest_dir.mkdir(parents=True, exist_ok=True)
                safe_code = re.sub(r"[^\w\-]", "_", str(act_code))
                dest = dest_dir / f"{safe_code}.json"
                dest.write_bytes(json_bytes)

                sha256 = val_res.sha256
                doc_id = f"{SOURCE_ID_PREFIX}_{sha256[:12]}"
                source_inst_id = f"{doc_id}_{int(datetime.utcnow().timestamp())}"

                primary, secondary, confidence, method = classify_document(title=title)

                prov = ProvenanceRecord(
                    document_id=doc_id,
                    source_instance_id=source_inst_id,
                    source_id=doc_id,
                    source_name=SOURCE_NAME,
                    source_authority=SourceAuthority.SECONDARY_COMMUNITY,
                    source_url=official_url,
                    local_file=str(dest),
                    sha256=sha256,
                    page=1,
                    extraction_method=ExtractionMethod.NATIVE_TEXT,
                    legal_domain=primary,
                )
                prov_registry.record_provenance(prov)

                doc_meta = DocumentMetadata(
                    document_id=doc_id,
                    source_instance_id=source_inst_id,
                    source_id=doc_id,
                    source_name=SOURCE_NAME,
                    source_type="legislation",
                    source_authority=SourceAuthority.SECONDARY_COMMUNITY,
                    legal_domain=primary,
                    secondary_domains=secondary,
                    classification_confidence=confidence,
                    classification_method=method,
                    title=title,
                    document_type=DocumentType.ACT,
                    official_url=official_url,
                    local_path=str(dest),
                    file_format="json",
                    sha256=sha256,
                    download_timestamp=datetime.utcnow(),
                    collection_method=CollectionMethod.ECOURTSINDIA_API,
                    validation_status="valid",
                    extraction_status="success",
                    extraction_method=ExtractionMethod.NATIVE_TEXT,
                )
                catalogue.upsert_document(doc_meta)
                log.info("Collected act from API", title=title, act_code=act_code)
                collected += 1

    log.info("indiacode.ecourtsindia.com API collection complete", collected=collected)
    return collected
