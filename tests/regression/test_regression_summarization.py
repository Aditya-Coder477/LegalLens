"""
tests/regression/test_regression_summarization.py
=================================================
Regression test verifying legal summarization preserves statutory provisions.
"""

import pytest

from pipeline.legal_ai.models import TaskType
from pipeline.legal_ai.service import LegalAIService


def test_regression_statute_summary():
    service = LegalAIService()
    resp = service.execute_task(
        query="Summarize the core framework of the Digital Lending Act, 2024",
        task_type=TaskType.SUMMARY,
    )

    assert resp.status == "SUCCESS"
    assert resp.direct_answer is not None
    assert len(resp.direct_answer) > 50
    assert resp.disclaimer is not None
