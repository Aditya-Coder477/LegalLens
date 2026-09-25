"""
tests/regression/test_regression_qa.py
======================================
Regression test verifying Legal AI grounded answer generation.
"""

import pytest

from pipeline.legal_ai.models import TaskType
from pipeline.legal_ai.service import LegalAIService


def test_regression_grounded_qa_answer():
    service = LegalAIService()
    response = service.execute_task(
        query="What authority is established under Section 3 of SYN-ACT-001?",
        task_type=TaskType.LEGAL_QA,
    )
    assert response.status == "SUCCESS"
    assert response.direct_answer is not None
    assert "authority" in (response.direct_answer or "").lower()
    assert len(response.evidence_refs) > 0
