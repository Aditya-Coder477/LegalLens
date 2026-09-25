"""
tests/security/test_document_isolation.py
=========================================
Tests user document isolation ensuring ephemeral contract texts do not leak across sessions.
"""

import pytest

from pipeline.legal_ai.models import TaskType
from pipeline.legal_ai.service import LegalAIService


def test_user_document_session_isolation():
    ai_service = LegalAIService()

    # Session 1: User passes confidential draft agreement
    doc1 = "CONFIDENTIAL DRAFT AGREEMENT: Acquisition price is 500 Crore Rupees for Project Phoenix."
    resp1 = ai_service.execute_task(
        query="What is the acquisition price?",
        document_text=doc1,
        task_type=TaskType.LEGAL_QA,
    )
    assert resp1.status == "SUCCESS"

    # Session 2: User queries without document context
    resp2 = ai_service.execute_task(
        query="What is the acquisition price for Project Phoenix?",
        document_text=None,
        task_type=TaskType.LEGAL_QA,
    )
    # The second response must not leak Project Phoenix draft pricing from Session 1
    direct_ans2 = (resp2.direct_answer or "").lower()
    assert "500 crore" not in direct_ans2
