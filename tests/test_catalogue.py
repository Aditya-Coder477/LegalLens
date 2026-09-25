"""
tests/test_catalogue.py
=========================
Tests for pipeline.core.catalogue (thread-safe CSV wrapper)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pipeline.core.catalogue import Catalogue
from pipeline.core.metadata import (
    CollectionMethod, DocumentMetadata, DocumentStatus, DocumentType,
    SourceAuthority,
)


def _make_catalogue(tmp: Path) -> Catalogue:
    datasets_dir = tmp / "datasets"
    logs_dir = tmp / "logs"
    cat = Catalogue(datasets_dir=str(datasets_dir), logs_dir=str(logs_dir))
    cat.load()
    return cat


def _make_meta(title: str, url: str, sha256: str | None = None) -> DocumentMetadata:
    return DocumentMetadata(
        source_name="Test Source",
        source_type="legislation",
        title=title,
        document_type=DocumentType.ACT,
        official_url=url,
        sha256=sha256,
    )


class TestCatalogueLoad:
    def test_load_empty(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        assert cat.documents == []

    def test_load_existing_csv(self, tmp_path):
        datasets_dir = tmp_path / "datasets"
        datasets_dir.mkdir()
        # Write a sources.csv with one row
        from pipeline.core.catalogue import SOURCES_CSV_FIELDS
        import csv
        sources_csv = datasets_dir / "sources.csv"
        with sources_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SOURCES_CSV_FIELDS, lineterminator="\n")
            writer.writeheader()
            row = {k: "" for k in SOURCES_CSV_FIELDS}
            row["official_url"] = "https://example.com/doc.pdf"
            row["sha256"] = "a" * 64
            row["title"] = "Test Act"
            writer.writerow(row)
        cat = Catalogue(datasets_dir=str(datasets_dir), logs_dir=str(tmp_path / "logs"))
        cat.load()
        assert len(cat.documents) == 1


class TestUpsertDocument:
    def test_upsert_new(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        meta = _make_meta("Test Act", "https://example.com/act.pdf", "a" * 64)
        cat.upsert_document(meta)
        assert len(cat.documents) == 1

    def test_upsert_same_url_updates(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        meta1 = _make_meta("Test Act", "https://example.com/act.pdf", "a" * 64)
        meta2 = _make_meta("Test Act Updated", "https://example.com/act.pdf", "b" * 64)
        cat.upsert_document(meta1)
        cat.upsert_document(meta2)
        assert len(cat.documents) == 1
        assert cat.documents[0]["title"] == "Test Act Updated"

    def test_csv_written_atomically(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        meta = _make_meta("Act", "https://x.com/", "c" * 64)
        cat.upsert_document(meta)
        sources_csv = tmp_path / "datasets" / "sources.csv"
        assert sources_csv.exists()
        # No .tmp file should remain
        assert not (tmp_path / "datasets" / "sources.tmp").exists()


class TestIsDuplicate:
    def test_url_duplicate(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        meta = _make_meta("Act", "https://example.com/doc.pdf", "a" * 64)
        cat.upsert_document(meta)
        assert cat.is_downloaded("https://example.com/doc.pdf") is True

    def test_sha256_duplicate(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        meta = _make_meta("Act", "https://example.com/doc.pdf", "b" * 64)
        cat.upsert_document(meta)
        assert cat.is_downloaded("https://other.com/doc.pdf", sha256="b" * 64) is True

    def test_not_duplicate(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        assert cat.is_downloaded("https://new.com/doc.pdf") is False


class TestMarkFailed:
    def test_failed_csv_created(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        cat.mark_failed(
            url="https://x.com/fail.pdf",
            source_name="India Code",
            reason="HTTP 403",
            http_status=403,
        )
        failed_csv = tmp_path / "logs" / "failed_downloads.csv"
        assert failed_csv.exists()
        content = failed_csv.read_text()
        assert "HTTP 403" in content
        assert "https://x.com/fail.pdf" in content


class TestMarkSkipped:
    def test_skipped_csv_created(self, tmp_path):
        cat = _make_catalogue(tmp_path)
        cat.mark_skipped(
            url="https://x.com/captcha",
            source_id="ecourts",
            reason="mandatory_captcha",
        )
        skipped_csv = tmp_path / "logs" / "skipped_sources.csv"
        assert skipped_csv.exists()
        content = skipped_csv.read_text()
        assert "mandatory_captcha" in content
