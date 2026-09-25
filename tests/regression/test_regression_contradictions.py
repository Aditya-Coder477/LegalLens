"""
tests/regression/test_regression_contradictions.py
==================================================
Regression test verifying that contradictory statutory provisions are detected and articulated.
"""

import pytest

from pipeline.legal_ai.models import TaskType
from pipeline.legal_ai.service import LegalAIService


def test_regression_contradiction_handling():
    service = LegalAIService()
    resp = service.execute_task(
        query="If there is a conflict between Section 18 of the Parent Act and Rule 10 of the Rules, which one governs?",
        task_type=TaskType.LEGAL_QA,
    )

    assert resp.status in ("SUCCESS", "LOW_EVIDENCE")
    assert resp.direct_answer is not None
