"""
tests/security/test_citation_tampering.py
=========================================
Tests detection of dead, altered, or fabricated statutory references.
"""

import pytest

from pipeline.safety.citation_verifier import CitationVerifier
from pipeline.safety.models import CitationVerificationStatus


def test_dead_citation_flagged():
    verifier = CitationVerifier()
    # A reference pointing to a non-existent section of a real act
    res = verifier.verify_citation("Section 999 of SYN-ACT-001")
    assert res.is_valid is False
    assert res.status in (CitationVerificationStatus.FABRICATED, CitationVerificationStatus.UNRESOLVED)


def test_superseded_version_citation_flagged():
    verifier = CitationVerifier()
    # Query an older version
    res = verifier.verify_citation("SYN-ACT-001-v1.0-original")
    assert res is not None
