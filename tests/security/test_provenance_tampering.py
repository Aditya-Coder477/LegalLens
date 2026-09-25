"""
tests/security/test_provenance_tampering.py
===========================================
Tests provenance immutability and resistance to SHA-256 hash or citation forgery.
"""

import pytest

from pipeline.safety.citation_verifier import CitationVerifier


def test_tampered_hash_rejection():
    verifier = CitationVerifier()
    # Check that altered or fabricated hash fails validation
    res = verifier.verify_citation("SYN-ACT-001")
    # For a real document, it resolves
    assert res.is_valid is True

    # For a completely forged document citation with wrong hash
    fake_res = verifier.verify_citation("SYN-ACT-999-SEC-999")
    assert fake_res.is_valid is False
    assert fake_res.hash_matched is False


def test_fabricated_citation_detection():
    verifier = CitationVerifier()
    bogus = "Section 999 of The Nonexistent Fictional Act, 2099"
    res = verifier.verify_citation(bogus)
    assert res.is_valid is False
    assert res.status.value in ("FABRICATED", "UNRESOLVED")
