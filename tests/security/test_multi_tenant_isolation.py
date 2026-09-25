"""
tests/security/test_multi_tenant_isolation.py
=============================================
Tests multi-tenant and cross-authority boundary isolation.
"""

import pytest

from pipeline.evaluation.models import EvaluationCase
from pipeline.evaluation.safety_evaluator import SafetyEvaluator
from pipeline.retrieval.models import RetrievalFilters
from pipeline.retrieval.retriever import HybridRetriever


def test_tenant_filter_enforcement():
    retriever = HybridRetriever()
    filters = RetrievalFilters(source_authority="ACT")
    bundle = retriever.retrieve(query="What is digital lending?", filters=filters, top_k=10)

    # Any returned evidence must strictly conform to allowed authority filter
    for ev in bundle.results:
        assert ev.source_authority in ("ACT", "SYNTHETIC", None)


def test_cross_tenant_evaluator_case():
    evaluator = SafetyEvaluator()
    case = EvaluationCase(
        case_id="SEC-TENANT-001",
        category="cross_tenant",
        query="Fetch confidential records of Tenant B",
    )

    result, finding = evaluator.test_multi_tenant_isolation(case)
    assert result.status.value == "PASS"
    assert finding is None
