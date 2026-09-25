"""
tests/evaluation/test_qa_evaluator.py
=====================================
Tests for QAEvaluator covering:
- Grounded QA
- Abstention / Unanswerable queries
- Contradictions
- Version awareness
"""

import pytest

from pipeline.evaluation.models import EvaluationCase, EvaluationStatus
from pipeline.evaluation.qa_evaluator import QAEvaluator


def test_qa_evaluator_grounded_qa():
    evaluator = QAEvaluator()
    case = EvaluationCase(
        case_id="QA-TEST-01",
        category="grounded_qa",
        query="What is the short title of Digital Lending Act?",
        expected_answer="Digital Lending Act, 2024",
    )

    result = evaluator.evaluate_grounded_qa(case)
    assert result.status in (EvaluationStatus.PASS, EvaluationStatus.FAIL)
    assert "confidence" in result.metrics
    assert result.latency_ms > 0


def test_qa_evaluator_unanswerable():
    evaluator = QAEvaluator()
    case = EvaluationCase(
        case_id="QA-TEST-UNANS",
        category="unanswerable_qa",
        query="What is the interplanetary tariff for lunar minerals under Indian maritime law?",
    )

    result = evaluator.evaluate_unanswerable(case)
    assert result.status in (EvaluationStatus.PASS, EvaluationStatus.FAIL)
    assert "abstained" in result.metrics


def test_qa_evaluator_contradiction():
    evaluator = QAEvaluator()
    case = EvaluationCase(
        case_id="QA-TEST-CONTRA",
        category="contradiction_qa",
        query="If there is a contradiction between Act Section 18 and Rule 10, which one overrides?",
    )

    result = evaluator.evaluate_contradiction(case)
    assert result.status in (EvaluationStatus.PASS, EvaluationStatus.FAIL)
    assert "conflict_identified" in result.metrics


def test_qa_evaluator_version():
    evaluator = QAEvaluator()
    case = EvaluationCase(
        case_id="QA-TEST-VER",
        category="version_qa",
        query="What was the penalty under Section 10 prior to the 2024 amendment?",
    )

    result = evaluator.evaluate_version_awareness(case)
    assert result.status in (EvaluationStatus.PASS, EvaluationStatus.FAIL)
    assert "version_acknowledged" in result.metrics
