"""
tests/test_html_extractor.py
==============================
Tests for pipeline.extractors.html_extractor
"""

from __future__ import annotations

import pytest
from pipeline.extractors.html_extractor import extract_html_string
from pipeline.core.metadata import ExtractionMethod


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Consumer Protection Act</title></head>
<body>
  <nav>Skip to content</nav>
  <h1>Consumer Protection Act, 2019</h1>
  <h2>Chapter I — Preliminary</h2>
  <p>This Act may be called the Consumer Protection Act, 2019.</p>
  <p>It extends to the whole of India.</p>
  <h2>Chapter II — Consumer Rights</h2>
  <p>Every consumer has the right to protection against marketing.</p>
  <footer>© Government of India</footer>
  <script>alert('test');</script>
</body>
</html>
"""


class TestHtmlExtractor:
    def test_basic_extraction(self):
        records = extract_html_string(
            SAMPLE_HTML,
            document_id="test_doc",
            source_url="https://example.com/cpa.html",
        )
        assert len(records) >= 1
        all_text = " ".join(r.text for r in records)
        assert "Consumer Protection Act" in all_text

    def test_script_stripped(self):
        records = extract_html_string(
            SAMPLE_HTML,
            document_id="test_doc",
            source_url="https://example.com/",
        )
        all_text = " ".join(r.text for r in records)
        assert "alert" not in all_text

    def test_nav_stripped(self):
        records = extract_html_string(
            SAMPLE_HTML,
            document_id="test_doc",
            source_url="https://example.com/",
        )
        all_text = " ".join(r.text for r in records)
        assert "Skip to content" not in all_text

    def test_footer_stripped(self):
        records = extract_html_string(
            SAMPLE_HTML,
            document_id="test_doc",
            source_url="https://example.com/",
        )
        all_text = " ".join(r.text for r in records)
        assert "Government of India" not in all_text

    def test_headings_preserved_as_sections(self):
        records = extract_html_string(
            SAMPLE_HTML,
            document_id="test_doc",
            source_url="https://example.com/",
        )
        headings = [r.heading for r in records if r.heading]
        assert any("Preliminary" in h or "Consumer Rights" in h for h in headings)

    def test_extraction_method_set(self):
        records = extract_html_string(
            SAMPLE_HTML,
            document_id="test_doc",
            source_url="https://example.com/",
        )
        for r in records:
            assert r.extraction_method == ExtractionMethod.HTML

    def test_empty_html(self):
        records = extract_html_string(
            "<html><body></body></html>",
            document_id="empty",
            source_url="https://example.com/",
        )
        assert records == []

    def test_document_id_set(self):
        records = extract_html_string(
            SAMPLE_HTML,
            document_id="my_doc_id",
            source_url="https://example.com/",
        )
        for r in records:
            assert r.document_id == "my_doc_id"

    def test_page_numbers_sequential(self):
        records = extract_html_string(
            SAMPLE_HTML,
            document_id="doc",
            source_url="https://example.com/",
        )
        for i, r in enumerate(records, start=1):
            assert r.page == i
