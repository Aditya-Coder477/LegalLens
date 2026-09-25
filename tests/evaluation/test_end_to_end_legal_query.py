"""
tests/evaluation/test_end_to_end_legal_query.py
===============================================
End-to-End integration test for LegalLens:
Verifies that a legal query progresses through:
Query Processing -> Hybrid Retrieval -> Legal Reasoning -> Citation Verification -> Safety Guardrails
and evaluates successfully.
"""

import pytest

from pipeline.legal_ai.service import LegalAIService
from pipeline.retrieval.retriever import HybridRetriever
from pipeline.safety.service import SafetyService


def test_end_to_end_query_lifecycle():
    query = "What constitutes digital lending under the Digital Lending Act, 2024?"

    retriever = HybridRetriever()
    ai_service = LegalAIService(retriever=retriever)
    safety_service = SafetyService()

    # 1. Retrieval
    bundle = retriever.retrieve(query=query, top_k=5)
    assert bundle is not None
    assert len(bundle.results) > 0

    # 2. Reasoning
    response = ai_service.execute_task(query=query)
    assert response is not None
    assert response.status == "SUCCESS"
    assert response.direct_answer is not None
    assert len(response.evidence_refs) > 0

    # 3. Citation Verification
    cit_res = safety_service.citation_verifier.verify_all_citations(response.evidence_refs)
    assert len(cit_res) > 0
    assert all(r.raw_citation in response.evidence_refs for r in cit_res)

    # 4. Safety Audit
    audit_res = safety_service.audit_response(response)
    assert audit_res.is_safe is True
    assert response.disclaimer is not None
    assert response.synthetic is True
