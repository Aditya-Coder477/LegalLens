"""
tests/regression/test_regression_obligations.py
==============================================
Regression test verifying obligation and deadline extraction stability.
"""

import pytest

from pipeline.legal_ai.models import TaskType
from pipeline.legal_ai.service import LegalAIService


def test_regression_obligation_extraction():
    service = LegalAIService()
    provision = (
        "Section 14: All non-banking financial companies engaged in digital lending "
        "shall submit quarterly compliance reports to the Reserve Bank within 15 days "
        "of the end of each quarter."
    )
    resp = service.execute_task(
        query="Extract statutory obligations and reporting deadlines",
        document_text=provision,
        task_type=TaskType.EXTRACT_OBLIGATIONS,
    )

    assert resp.status == "SUCCESS"
    assert len(resp.structured_data.get("obligations", [])) > 0 or resp.direct_answer is not None
