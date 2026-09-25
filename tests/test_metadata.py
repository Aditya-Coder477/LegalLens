"""
tests/test_metadata.py
========================
Tests for pipeline.core.metadata — Pydantic models and enums.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.core.metadata import (
    CollectionMethod,
    DocumentMetadata,
    DocumentStatus,
    DocumentType,
    ExtractionMethod,
    FailedDownload,
    LegalDomain,
    PageRecord,
    SkippedSource,
    SourceAuthority,
)


class TestSourceAuthorityEnum:
    def test_all_values_exist(self):
        values = {a.value for a in SourceAuthority}
        assert "PRIMARY_OFFICIAL" in values
        assert "SECONDARY_COMMUNITY" in values
        assert "OFFICIAL_COURT" in values
        assert "USER_PROVIDED" in values

    def test_string_construction(self):
        assert SourceAuthority("PRIMARY_OFFICIAL") == SourceAuthority.PRIMARY_OFFICIAL


class TestLegalDomain:
    def test_count_at_least_50(self):
        domains = [d for d in LegalDomain if d != LegalDomain.UNCLASSIFIED]
        assert len(domains) >= 50, f"Expected >= 50 domains, got {len(domains)}"

    def test_known_domains_present(self):
        domain_values = {d.value for d in LegalDomain}
        assert "Criminal Law" in domain_values
        assert "Contract Law" in domain_values
        assert "Information Technology and Cyber Law" in domain_values
        assert "Data Protection and Privacy Law" in domain_values
        assert "Emerging Technology / AI / Digital Regulation" in domain_values


class TestDocumentMetadata:
    def _make_meta(self, **overrides) -> DocumentMetadata:
        defaults = {
            "source_name": "India Code",
            "source_type": "legislation",
            "title": "Indian Contract Act, 1872",
            "document_type": DocumentType.ACT,
            "official_url": "https://www.indiacode.nic.in/handle/123456789/2187",
        }
        defaults.update(overrides)
        return DocumentMetadata(**defaults)

    def test_basic_creation(self):
        meta = self._make_meta()
        assert meta.source_name == "India Code"
        assert meta.title == "Indian Contract Act, 1872"
        assert meta.source_authority == SourceAuthority.PRIMARY_OFFICIAL

    def test_sha256_validation_valid(self):
        meta = self._make_meta(sha256="a" * 64)
        assert meta.sha256 == "a" * 64

    def test_sha256_validation_invalid(self):
        with pytest.raises(ValidationError):
            self._make_meta(sha256="short_hash")

    def test_sha256_none_is_valid(self):
        meta = self._make_meta(sha256=None)
        assert meta.sha256 is None

    def test_to_csv_row_includes_all_fields(self):
        meta = self._make_meta()
        row = meta.to_csv_row()
        assert "source_id" in row
        assert "title" in row
        assert "sha256" in row
        assert "source_authority" in row
        # Enums should be serialized to string
        assert isinstance(row["source_authority"], str)

    def test_secondary_domains_csv_pipe_separated(self):
        meta = self._make_meta(secondary_domains=["Criminal Law", "Contract Law"])
        row = meta.to_csv_row()
        assert "|" in row["secondary_domains"]

    def test_uuid_auto_generated(self):
        meta1 = self._make_meta()
        meta2 = self._make_meta()
        assert meta1.source_id != meta2.source_id

    def test_multilingual_fields_defaults(self):
        meta = self._make_meta()
        assert meta.translation_available is False
        assert meta.translation_source is None
        assert meta.original_language is None


class TestPageRecord:
    def test_word_count_auto(self):
        record = PageRecord(
            document_id="doc123",
            page=1,
            text="This is a test document with seven words here",
            source_url="https://example.com/doc.pdf",
        )
        assert record.word_count is not None
        assert record.word_count > 0

    def test_page_must_be_positive(self):
        with pytest.raises(ValidationError):
            PageRecord(
                document_id="doc123",
                page=0,
                text="test",
                source_url="https://example.com/",
            )

    def test_ocr_fields_optional(self):
        record = PageRecord(
            document_id="doc123",
            page=1,
            text="text",
            source_url="https://example.com/",
            ocr_used=True,
            ocr_engine="tesseract",
            ocr_language="eng",
            ocr_confidence=87.5,
        )
        assert record.ocr_used is True
        assert record.ocr_engine == "tesseract"


class TestFailedDownload:
    def test_creation(self):
        f = FailedDownload(
            url="https://example.com/file.pdf",
            source_id="india_code",
            source_name="India Code",
            reason="HTTP 403",
            http_status=403,
        )
        assert f.reason == "HTTP 403"
        assert f.retry_count == 0

    def test_timestamp_auto(self):
        f = FailedDownload(
            url="https://x.com",
            source_id="s",
            source_name="S",
            reason="timeout",
        )
        assert f.timestamp is not None
