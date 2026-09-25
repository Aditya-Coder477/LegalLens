"""
tests/test_provenance.py
=========================
Tests for pipeline.provenance.provenance
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pipeline.provenance.provenance import ProvenanceRecord, ProvenanceRegistry
from pipeline.core.metadata import ExtractionMethod, SourceAuthority


def _make_record(**overrides) -> ProvenanceRecord:
    defaults = {
        "document_id": "doc123",
        "source_id": "india_code_001",
        "source_name": "India Code",
        "source_authority": SourceAuthority.PRIMARY_OFFICIAL,
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2187",
        "local_file": "legal-data/raw/india_code/acts/contract_act.pdf",
        "sha256": "a" * 64,
        "extraction_method": ExtractionMethod.PDF_TEXT,
        "legal_domain": "Contract Law",
    }
    defaults.update(overrides)
    return ProvenanceRecord(**defaults)


class TestProvenanceRecord:
    def test_creation(self):
        rec = _make_record(page=1, section="8")
        assert rec.document_id == "doc123"
        assert rec.page == 1
        assert rec.source_authority == SourceAuthority.PRIMARY_OFFICIAL

    def test_to_jsonl_line(self):
        rec = _make_record(page=5)
        line = rec.to_jsonl_line()
        data = json.loads(line)
        assert data["document_id"] == "doc123"
        assert data["page"] == 5
        assert data["source_authority"] == "PRIMARY_OFFICIAL"

    def test_unique_provenance_ids(self):
        r1 = _make_record()
        r2 = _make_record()
        assert r1.provenance_id != r2.provenance_id

    def test_ocr_fields(self):
        rec = _make_record(
            ocr_used=True,
            ocr_engine="tesseract",
            ocr_language="eng",
            ocr_confidence=87.5,
        )
        assert rec.ocr_used is True
        assert rec.ocr_confidence == 87.5


class TestProvenanceRegistry:
    def test_record_and_read_back(self, tmp_path):
        output_dir = str(tmp_path / "metadata")
        registry = ProvenanceRegistry(output_dir=output_dir)
        rec = _make_record(page=1)
        registry.record(rec)
        all_records = registry.all_records()
        assert len(all_records) == 1
        assert all_records[0].document_id == "doc123"

    def test_batch_record(self, tmp_path):
        output_dir = str(tmp_path / "metadata")
        registry = ProvenanceRegistry(output_dir=output_dir)
        records = [_make_record(page=i) for i in range(1, 6)]
        registry.record_batch(records)
        all_records = registry.all_records()
        assert len(all_records) == 5

    def test_provenance_jsonl_format(self, tmp_path):
        output_dir = str(tmp_path / "metadata")
        registry = ProvenanceRegistry(output_dir=output_dir)
        rec = _make_record(page=3)
        registry.record(rec)
        # Each line should be valid JSON
        jsonl_path = Path(output_dir) / "provenance.jsonl"
        for line in jsonl_path.open():
            line = line.strip()
            if line:
                data = json.loads(line)
                assert "document_id" in data
                assert "sha256" in data

    def test_check_discrepancy_same_hash(self, tmp_path):
        registry = ProvenanceRegistry(str(tmp_path))
        result = registry.check_discrepancy(
            document_id="doc1",
            primary_sha256="a" * 64,
            secondary_sha256="a" * 64,
            primary_source="India Code",
            secondary_source="eCourtsIndia API",
        )
        assert result is False

    def test_check_discrepancy_different_hash(self, tmp_path):
        registry = ProvenanceRegistry(str(tmp_path))
        result = registry.check_discrepancy(
            document_id="doc1",
            primary_sha256="a" * 64,
            secondary_sha256="b" * 64,
            primary_source="India Code",
            secondary_source="eCourtsIndia API",
        )
        assert result is True
