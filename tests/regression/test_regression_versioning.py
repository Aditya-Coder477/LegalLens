"""
tests/regression/test_regression_versioning.py
==============================================
Regression test verifying version-aware and historical law inquiries.
"""

import pytest

from pipeline.legal_ai.models import TaskType
from pipeline.legal_ai.service import LegalAIService


def test_regression_versioning_query():
    service = LegalAIService()
    resp = service.execute_task(
        query="What changes were introduced in the 2024 amendment of the Digital Lending Act?",
        task_type=TaskType.LEGAL_QA,
    )

    assert resp is not None
    assert resp.status in ("SUCCESS", "LOW_EVIDENCE")
