"""
pipeline/core/catalogue.py
==========================
Thread-safe read/write wrapper around the CSV catalogue files.

Managed files:
  - legal-data/datasets/sources.csv    (master document catalogue)
  - legal-data/logs/failed_downloads.csv
  - legal-data/logs/skipped_sources.csv

Key guarantees:
  - Atomic writes: always write to .tmp then os.replace()
  - Idempotent upsert: same URL + SHA-256 is never double-inserted
  - Fast O(1) duplicate lookups via in-memory sets
  - Thread-safe: all mutations protected by threading.Lock

Usage:
    catalogue = Catalogue()
    catalogue.load()

    if not catalogue.is_downloaded(url="https://...", sha256="abc..."):
        # ... download the file ...
        catalogue.upsert_document(metadata)

    catalogue.mark_failed(url="https://...", reason="HTTP 403", http_status=403)
"""

from __future__ import annotations

import csv
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from pipeline.core.metadata import DocumentMetadata, FailedDownload, SkippedSource
from pipeline.core.logger import get_logger

log = get_logger("catalogue")


# ── CSV column definitions ────────────────────────────────────────

SOURCES_CSV_FIELDS = [
    "source_id", "document_id", "source_instance_id", "source_name", "source_type", "source_authority",
    "legal_domain", "secondary_domains", "classification_confidence",
    "classification_method", "title", "document_type", "official_url",
    "download_url", "local_path", "file_format", "publication_date",
    "effective_date", "repeal_date", "amendment_date", "status",
    "ministry", "department", "jurisdiction", "country", "state",
    "act_number", "act_year", "section_number", "language",
    "original_language", "translation_available", "translation_source",
    "sha256", "file_size_bytes", "download_timestamp", "last_verified",
    "collection_method", "verification_status", "validation_status",
    "validation_error", "extraction_status", "extraction_method",
    "ocr_used", "ocr_pages", "extractor_version", "http_status",
    "content_type", "etag", "last_modified_header",
    "document_version_group_id", "version_label",
    "dspace_handle", "act_id",
]

FAILED_CSV_FIELDS = [
    "url", "source_id", "source_name", "reason",
    "http_status", "error_type", "timestamp", "retry_count",
    "recommended_action",
]

SKIPPED_CSV_FIELDS = [
    "url", "source_id", "reason", "timestamp", "note",
]


class Catalogue:
    """
    Thread-safe catalogue manager for sources.csv and log CSVs.
    """

    def __init__(
        self,
        datasets_dir: str = "legal-data/datasets",
        logs_dir: str = "legal-data/logs",
    ) -> None:
        self._datasets_dir = Path(datasets_dir)
        self._logs_dir = Path(logs_dir)
        self._sources_path = self._datasets_dir / "sources.csv"
        self._failed_path = self._logs_dir / "failed_downloads.csv"
        self._skipped_path = self._logs_dir / "skipped_sources.csv"

        self._lock = threading.Lock()

        # In-memory sets for O(1) duplicate lookups
        self._known_urls: set[str] = set()
        self._known_hashes: set[str] = set()

        # In-memory list of all document rows (for dedup / report generation)
        self._documents: list[dict] = []

    def load(self) -> None:
        """Load existing catalogue from disk into memory."""
        self._known_urls.clear()
        self._known_hashes.clear()
        self._documents.clear()

        if self._sources_path.exists():
            with self._sources_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._documents.append(row)
                    if row.get("official_url"):
                        self._known_urls.add(self._normalise_url(row["official_url"]))
                    if row.get("sha256"):
                        self._known_hashes.add(row["sha256"].lower())

        log.info(
            "Catalogue loaded",
            documents=len(self._documents),
            known_urls=len(self._known_urls),
            known_hashes=len(self._known_hashes),
        )

    def is_downloaded(self, url: str, sha256: Optional[str] = None) -> bool:
        """
        Return True if this URL (or SHA-256) is already in the catalogue.
        Used by --resume logic.
        """
        url_known = self._normalise_url(url) in self._known_urls
        if sha256:
            return url_known or sha256.lower() in self._known_hashes
        return url_known

    def upsert_document(self, metadata: DocumentMetadata) -> None:
        """
        Add a document to sources.csv. If the URL is already present, update it.
        Atomic write: writes to .tmp then os.replace().
        """
        row = metadata.to_csv_row()
        norm_url = self._normalise_url(metadata.official_url)

        with self._lock:
            # Update in-memory state
            self._known_urls.add(norm_url)
            if metadata.sha256:
                self._known_hashes.add(metadata.sha256.lower())

            # Find and update existing row or append new
            found = False
            for i, existing in enumerate(self._documents):
                if self._normalise_url(existing.get("official_url", "")) == norm_url:
                    self._documents[i] = row
                    found = True
                    break
            if not found:
                self._documents.append(row)

            self._write_sources_csv()

        log.info("Upserted document", title=metadata.title, url=metadata.official_url)

    def mark_failed(
        self,
        url: str,
        reason: str,
        source_id: str = "",
        source_name: str = "",
        http_status: Optional[int] = None,
        error_type: Optional[str] = None,
        recommended_action: Optional[str] = None,
    ) -> None:
        """Append a failure record to failed_downloads.csv with secrets redacted."""
        clean_url = self._redact_url(url)
        clean_reason = self._redact_url(reason)
        record = FailedDownload(
            url=clean_url,
            source_id=source_id,
            source_name=source_name,
            reason=clean_reason,
            http_status=http_status,
            error_type=error_type,
            recommended_action=recommended_action,
        )
        with self._lock:
            self._append_csv(self._failed_path, FAILED_CSV_FIELDS, record.model_dump())

        log.log_download_failed(url=clean_url, reason=clean_reason, http_status=http_status)

    def mark_skipped(
        self,
        url: str,
        source_id: str,
        reason: str,
        note: Optional[str] = None,
    ) -> None:
        """Append a skip record to skipped_sources.csv with secrets redacted."""
        clean_url = self._redact_url(url)
        clean_reason = self._redact_url(reason)
        record = SkippedSource(
            url=clean_url,
            source_id=source_id,
            reason=clean_reason,
            note=note,
        )
        with self._lock:
            self._append_csv(self._skipped_path, SKIPPED_CSV_FIELDS, record.model_dump())

        log.log_skipped(url=clean_url, reason=clean_reason)

    def is_skipped(self, url: str) -> bool:
        """Check if a URL was recorded as skipped in skipped_sources.csv."""
        if not self._skipped_path.exists():
            return False
        norm = self._normalise_url(url)
        with self._lock:
            with self._skipped_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return any(self._normalise_url(row.get("url", "")).startswith(norm) for row in reader)


    @property
    def documents(self) -> list[dict]:
        """Read-only snapshot of all catalogue rows."""
        with self._lock:
            return list(self._documents)

    @property
    def known_hashes(self) -> set[str]:
        """Read-only snapshot of all known SHA-256 hashes."""
        with self._lock:
            return set(self._known_hashes)

    @staticmethod
    def _redact_url(text: str) -> str:
        """Redact sensitive query parameters from URLs or error messages."""
        if not text:
            return ""
        from pipeline.core.http_client import redact_secrets_from_url
        # If it contains spaces, could be an error message containing a URL
        words = text.split()
        redacted_words = [redact_secrets_from_url(w) if "http" in w else w for w in words]
        return " ".join(redacted_words)

    @staticmethod
    def _normalise_url(url: str) -> str:
        """Normalise URL for comparison (lowercase, strip trailing slash, remove fragment)."""
        url = url.strip().rstrip("/").lower()
        if "#" in url:
            url = url[: url.index("#")]
        return url

    def _write_sources_csv(self) -> None:
        """Atomically rewrite sources.csv with current in-memory documents."""
        self._datasets_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self._sources_path.with_suffix(".tmp")
        with tmp_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=SOURCES_CSV_FIELDS,
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(self._documents)
        os.replace(tmp_path, self._sources_path)

    def _append_csv(self, path: Path, fields: list[str], row: dict) -> None:
        """Append one row to a CSV log file, creating header if needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fields,
                extrasaction="ignore",
                lineterminator="\n",
            )
            if write_header:
                writer.writeheader()
            # Serialize any non-string values
            serialised = {
                k: (v.isoformat() if isinstance(v, datetime) else str(v) if v is not None else "")
                for k, v in row.items()
            }
            writer.writerow(serialised)
