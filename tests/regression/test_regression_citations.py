"""
tests/regression/test_regression_citations.py
============================================
Regression test verifying citation resolution for known KB provisions.
"""

import pytest

from pipeline.safety.citation_verifier import CitationVerifier


def test_regression_valid_citations():
    verifier = CitationVerifier()
    res = verifier.verify_citation("SYN-ACT-001")
    assert res.is_valid is True
    assert res.hash_matched is True
