"""
tests/security/test_oversized_payloads.py
=========================================
Tests system behavior when handling oversized documents or queries exceeding context limits.
"""

import pytest

from pipeline.legal_ai.context_builder import ContextBuilder
from pipeline.legal_ai.service import LegalAIService


def test_oversized_document_truncation_safety():
    from pipeline.legal_ai.models import UserFact
    from pipeline.retrieval.models import EvidenceBundle

    builder = ContextBuilder(max_tokens=1000)
    huge_text = "This is a legal clause repeating endlessly. " * 5000
    user_facts = [UserFact(text=huge_text, fact_id="F1")]
    bundle = EvidenceBundle(query="What are the conditions?", normalized_query="what conditions")
    built = builder.build(
        bundle=bundle,
        user_facts=user_facts,
    )

    assert built is not None
    assert built.token_estimate <= 1500


def test_oversized_query_handling():
    ai_service = LegalAIService()
    huge_query = "What is the penalty? " * 300
    resp = ai_service.execute_task(query=huge_query)
    assert resp is not None
    assert resp.status in ("SUCCESS", "LOW_EVIDENCE", "NO_EVIDENCE")
