"""
tests/test_dedup.py
====================
Tests for pipeline.dedup.deduplicator
"""

from __future__ import annotations

import pytest
from pipeline.dedup.deduplicator import (
    Deduplicator,
    normalise_url,
    normalise_title,
    title_similarity,
)


class TestNormaliseUrl:
    def test_removes_trailing_slash(self):
        assert normalise_url("https://example.com/page/") == normalise_url("https://example.com/page")

    def test_removes_fragment(self):
        assert normalise_url("https://x.com/doc#section-3") == normalise_url("https://x.com/doc")

    def test_strips_utm_params(self):
        assert normalise_url("https://x.com/doc?utm_source=foo") == normalise_url("https://x.com/doc")

    def test_lowercases(self):
        assert normalise_url("HTTPS://Example.COM/Path") == normalise_url("https://example.com/path")

    def test_sorts_query_params(self):
        url1 = normalise_url("https://x.com/doc?b=2&a=1")
        url2 = normalise_url("https://x.com/doc?a=1&b=2")
        assert url1 == url2


class TestNormaliseTitle:
    def test_same_after_normalise(self):
        t1 = normalise_title("Indian Penal Code 1860")
        t2 = normalise_title("The Indian Penal Code, 1860")
        # Both should normalise to same base (year stripped, "the" removed)
        assert t1 == t2 or title_similarity(t1, t2) >= 0.95


class TestTitleSimilarity:
    def test_identical_titles(self):
        assert title_similarity("Indian Contract Act", "Indian Contract Act") == 1.0

    def test_similar_titles(self):
        sim = title_similarity(
            "Indian Contract Act, 1872",
            "Indian Contract Act 1872",
        )
        assert sim >= 0.85

    def test_very_different_titles(self):
        sim = title_similarity("Consumer Protection", "Nuclear Energy")
        assert sim < 0.5

    def test_threshold_dedup(self):
        sim = title_similarity(
            "Code of Criminal Procedure",
            "Code of Criminal Procedure, 1973",
        )
        assert sim >= 0.90


class TestDeduplicator:
    def _make_docs(self):
        return [
            {
                "source_id": "doc1",
                "official_url": "https://example.com/ita-2000.pdf",
                "title": "Information Technology Act, 2000",
                "sha256": "a" * 64,
                "act_number": "21",
                "act_year": "2000",
                "source_name": "India Code",
            },
            {
                "source_id": "doc2",
                "official_url": "https://example.com/ita-2000.pdf",  # same URL
                "title": "IT Act 2000",
                "sha256": "b" * 64,
                "act_number": "21",
                "act_year": "2000",
                "source_name": "India Code",
            },
            {
                "source_id": "doc3",
                "official_url": "https://example.com/ipc-1860.pdf",
                "title": "Indian Penal Code, 1860",
                "sha256": "a" * 64,  # same hash as doc1
                "act_number": "45",
                "act_year": "1860",
                "source_name": "India Code",
            },
        ]

    def test_url_dedup_detected(self):
        docs = self._make_docs()
        deduplicator = Deduplicator()
        groups = deduplicator._url_dedup(docs)
        assert len(groups) >= 1
        assert any(g.reason == "url_duplicate" for g in groups)

    def test_sha256_dedup_detected(self):
        docs = self._make_docs()
        deduplicator = Deduplicator()
        groups = deduplicator._sha256_dedup(docs)
        assert len(groups) >= 1
        assert any(g.reason == "sha256_duplicate" for g in groups)

    def test_metadata_dedup(self):
        docs = [
            {
                "source_id": "d1",
                "official_url": "https://a.com/act1.pdf",
                "title": "Consumer Protection Act",
                "sha256": "c" * 64,
                "act_number": "35",
                "act_year": "2019",
                "source_name": "India Code",
            },
            {
                "source_id": "d2",
                "official_url": "https://b.com/act1.pdf",
                "title": "Consumer Protection Act 2019",
                "sha256": "d" * 64,
                "act_number": "35",
                "act_year": "2019",
                "source_name": "India Code",
            },
        ]
        deduplicator = Deduplicator()
        groups = deduplicator._metadata_dedup(docs)
        assert len(groups) >= 1

    def test_full_run_and_report(self, tmp_path):
        docs = self._make_docs()
        deduplicator = Deduplicator(similarity_threshold=0.92)
        groups = deduplicator.run(docs)
        report_path = deduplicator.save_report(groups, output_dir=str(tmp_path))
        assert report_path.exists()
        import json
        report = json.loads(report_path.read_text())
        assert "total_duplicate_groups" in report
        assert report["total_duplicate_groups"] >= 0
