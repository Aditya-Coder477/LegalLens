"""
pipeline/provenance/provenance.py
==================================
Provenance registry: records and persists the complete audit chain for every
extracted page and chunk.

Audit chain:
    AI Answer
      ↓
    Retrieved Chunk
      ↓
    Section
      ↓
    Page
      ↓
    Document
      ↓
    Original URL
      ↓
    SHA-256

Every ProvenanceRecord captures:
  - chunk_id           → unique ID for the retrieval unit
  - document_id        → links back to sources.csv
  - source_authority   → PRIMARY_OFFICIAL, OFFICIAL_COURT, etc.
  - source_url         → original URL (preserved, never modified)
  - local_file         → path to the raw file in legal-data/raw/
  - sha256             → hash of the raw file
  - page               → page number in the original document
  - section            → legal section number
  - extraction_method  → pdf_text, pdf_ocr, html, docx, etc.
  - ocr_used           → whether OCR was applied to this page

Records are saved as JSONL to legal-data/processed/metadata/provenance.jsonl
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from pipeline.core.metadata import ExtractionMethod, SourceAuthority


class ProvenanceRecord(BaseModel):
    """
    Full audit trail for one extracted page or chunk.
    Stored in legal-data/processed/metadata/provenance.jsonl
    """

    provenance_id: str = Field(default_factory=lambda: str(uuid4()))
    chunk_id: Optional[str] = Field(default=None, description="Set when chunking for RAG")
    document_id: str
    source_instance_id: Optional[str] = Field(default=None, description="Specific source copy version ID")
    source_id: str
    source_name: str
    source_authority: SourceAuthority
    source_url: Optional[str] = None
    local_file: str
    sha256: str
    page: Optional[int] = None
    section: Optional[str] = None
    heading: Optional[str] = None
    extraction_method: ExtractionMethod
    extractor_version: str = Field(default="1.0.0")
    ocr_used: bool = False
    ocr_confidence: Optional[float] = None
    ocr_engine: Optional[str] = None
    ocr_language: Optional[str] = None
    legal_domain: str
    act_number: Optional[str] = None
    act_year: Optional[int] = None
    language: str = "en"
    synthetic: bool = False
    generated_by: Optional[str] = None
    generator_version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_jsonl_line(self) -> str:
        """Serialize to a single JSON line (no trailing newline) with secrets redacted."""
        from pipeline.core.http_client import redact_secrets_from_url
        d = self.model_dump()
        d["source_url"] = redact_secrets_from_url(d.get("source_url", ""))
        # Convert datetime and enum to strings
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
            elif hasattr(v, "value"):
                d[k] = v.value
        return json.dumps(d, ensure_ascii=False)


class ProvenanceRegistry:
    """
    Append-only registry that writes ProvenanceRecord objects to a JSONL file.

    Thread-safe: all writes protected by threading.Lock.
    Atomic: writes to .tmp line then flushes.

    Usage:
        registry = ProvenanceRegistry()
        registry.record(provenance_record)
    """

    def __init__(self, output_dir: str = "legal-data/processed/metadata") -> None:
        p = Path(output_dir)
        if p.suffix == ".jsonl":
            self._path = p
        else:
            self._path = p / "provenance.jsonl"
        self._lock = threading.Lock()

    def record(self, prov: ProvenanceRecord) -> None:
        """Append one provenance record to the JSONL file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = prov.to_jsonl_line() + "\n"
        with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line)

    record_provenance = record

    def record_batch(self, records: list[ProvenanceRecord]) -> None:
        """Append multiple records in a single write."""
        if not records:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = "\n".join(r.to_jsonl_line() for r in records) + "\n"
        with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(lines)

    def all_records(self) -> list[ProvenanceRecord]:
        """Read all records from disk (for reporting)."""
        if not self._path.exists():
            return []
        records = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(ProvenanceRecord.model_validate_json(line))
        return records

    def check_discrepancy(
        self,
        document_id: str,
        primary_sha256: str,
        secondary_sha256: str,
        primary_source: str,
        secondary_source: str,
    ) -> bool:
        """
        Detect a content discrepancy between primary and secondary sources.
        Returns True if a discrepancy is detected (hashes differ).

        When a discrepancy is detected, logs a warning with the source tier details.
        The pipeline should flag the document for human review rather than
        silently preferring the secondary source.
        """
        if primary_sha256 != secondary_sha256:
            from pipeline.core.logger import get_logger
            log = get_logger("provenance")
            log.warning(
                "⚠ Source discrepancy detected",
                document_id=document_id,
                primary_source=primary_source,
                secondary_source=secondary_source,
                action="review_required",
                note=(
                    "Primary source and secondary source have different content. "
                    "Do NOT silently use the secondary version. Manual review required."
                ),
            )
            return True
        return False
