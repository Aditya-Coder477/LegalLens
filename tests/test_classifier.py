"""
tests/test_classifier.py
==========================
Tests for the keyword classifier and classification orchestrator.
"""

from __future__ import annotations

import pytest

from pipeline.classification.keyword_classifier import (
    classify,
    DOMAIN_KEYWORDS,
    EXACT_TITLE_PATTERNS,
)
from pipeline.dedup.deduplicator import normalise_title
from pipeline.core.metadata import LegalDomain


class TestNormaliseTitle:
    def test_basic_lowercasing(self):
        assert normalise_title("Indian Contract Act") == normalise_title("indian contract act")

    def test_removes_common_words(self):
        result = normalise_title("The Indian Penal Code, 1860")
        assert "the" not in result
        assert "1860" not in result  # year stripped

    def test_punctuation_removed(self):
        result = normalise_title("Code of Civil Procedure, 1908")
        assert "," not in result


class TestExactTitlePatterns:
    def test_ipc_classified_criminal(self):
        domain, secondary, confidence, method = classify(
            title="Indian Penal Code, 1860"
        )
        assert domain == LegalDomain.CRIMINAL_LAW.value
        assert confidence >= 0.90
        assert method == "keyword"

    def test_ita_classified_it(self):
        domain, _, confidence, _ = classify(
            title="Information Technology Act, 2000"
        )
        assert domain == LegalDomain.IT_CYBER_LAW.value

    def test_dpdpa_classified_privacy(self):
        domain, _, _, _ = classify(
            title="Digital Personal Data Protection Act, 2023"
        )
        assert domain == LegalDomain.DATA_PROTECTION_PRIVACY.value

    def test_contract_act(self):
        domain, _, confidence, _ = classify(
            title="Indian Contract Act, 1872"
        )
        assert domain == LegalDomain.CONTRACT_LAW.value

    def test_constitution(self):
        domain, _, _, _ = classify(title="Constitution of India")
        assert domain == LegalDomain.CONSTITUTIONAL_LAW.value

    def test_ibc(self):
        domain, _, _, _ = classify(title="Insolvency and Bankruptcy Code, 2016")
        assert domain == LegalDomain.INSOLVENCY_BANKRUPTCY.value

    def test_rera(self):
        domain, _, _, _ = classify(
            title="Real Estate (Regulation and Development) Act, 2016"
        )
        assert domain == LegalDomain.PROPERTY_REAL_ESTATE.value


class TestKeywordMatching:
    def test_ministry_hint_boosts_score(self):
        domain, _, confidence, _ = classify(
            title="Some Obscure Regulations",
            ministry="Ministry of Electronics and Information Technology",
        )
        # Should classify into IT/data domain with reasonable confidence
        assert domain in (
            LegalDomain.IT_CYBER_LAW.value,
            LegalDomain.DATA_PROTECTION_PRIVACY.value,
        )

    def test_unclassified_with_no_signals(self):
        domain, _, confidence, _ = classify(title="Random XYZ Report 2023")
        assert domain == LegalDomain.UNCLASSIFIED.value
        assert confidence == 0.0

    def test_multiple_keyword_matches_raise_confidence(self):
        _, _, confidence, _ = classify(
            title="Criminal Code",
            extra_text="offence murder arrest bail cognizable non-cognizable POCSO",
        )
        assert confidence >= 0.40

    def test_secondary_domains_returned(self):
        _, secondary, _, _ = classify(
            title="Companies Act 2013",
            ministry="Ministry of Corporate Affairs",
            extra_text="insolvency bankruptcy NCLT liquidation",
        )
        # Primary will be commercial_corporate; secondary might include insolvency
        # At minimum secondary should be a list
        assert isinstance(secondary, list)


class TestDomainKeywordsCoverage:
    def test_all_50_domains_have_keywords(self):
        """Verify each LegalDomain (except UNCLASSIFIED) has keyword entries."""
        covered = set(DOMAIN_KEYWORDS.keys())
        for domain in LegalDomain:
            if domain == LegalDomain.UNCLASSIFIED:
                continue
            assert domain.value in covered, f"Missing keywords for: {domain.value}"
