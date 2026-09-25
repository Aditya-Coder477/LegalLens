"""
tests/regression/test_regression_clauses.py
===========================================
Regression test verifying clause analysis extraction stability.
"""

import pytest

from pipeline.legal_ai.models import TaskType
from pipeline.legal_ai.service import LegalAIService


def test_regression_clause_analysis_structure():
    service = LegalAIService()
    clause_text = (
        "Section 12: Every licensed digital lending platform shall maintain an escrow account "
        "with a scheduled commercial bank within 30 days of license grant. Failure to comply shall attract penalty."
    )
    resp = service.execute_task(
        query="Analyze Section 12 clause obligations and deadlines",
        document_text=clause_text,
        task_type=TaskType.CLAUSE_ANALYSIS,
    )

    assert resp.status == "SUCCESS"
    assert resp.direct_answer is not None or "obligations" in resp.structured_data
    assert len(resp.structured_data.get("obligations", [])) > 0 or len(resp.claims) > 0
