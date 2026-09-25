"""
tests/evaluation/test_retrieval_evaluator.py
============================================
Tests for RetrievalEvaluator across lexical, semantic, hybrid, rerank, and expansion.
"""

import pytest

from pipeline.evaluation.models import EvaluationCase, EvaluationStatus
from pipeline.evaluation.retrieval_evaluator import RetrievalEvaluator, is_chunk_relevant


def test_is_chunk_relevant():
    case = EvaluationCase(
        case_id="RET-001",
        category="retrieval",
        expected_chunk_ids=["SYN-ACT-001-CH-I-S01"],
        expected_sections=["SYN-ACT-001-SEC-1"],
    )

    assert is_chunk_relevant("SYN-ACT-001-CH-I-S01", case) is True
    assert is_chunk_relevant("SYN-ACT-001-CH-I-S02", case) is False


def test_retrieval_evaluator_single_case():
    evaluator = RetrievalEvaluator()
    case = EvaluationCase(
        case_id="RET-TEST-01",
        category="retrieval",
        query="What are the definitions in Digital Lending Act?",
        expected_documents=["SYN-ACT-001"],
        expected_sections=["SYN-ACT-001-SEC-2"],
    )

    result = evaluator.evaluate_case(case, strategy="hybrid", top_k=10)
    assert result.status in (EvaluationStatus.PASS, EvaluationStatus.FAIL)
    assert "recall@10" in result.metrics
    assert "mrr" in result.metrics
    assert "ndcg@10" in result.metrics
    assert result.latency_ms > 0


def test_retrieval_evaluator_benchmark_comparison():
    evaluator = RetrievalEvaluator()
    cases = [
        EvaluationCase(
            case_id="RET-TEST-02",
            category="retrieval",
            query="digital lending provider registration requirements",
            expected_documents=["SYN-ACT-001"],
        )
    ]

    benchmark = evaluator.evaluate_benchmark(cases, strategies=["lexical", "hybrid"])
    assert "metrics_by_strategy" in benchmark
    assert "lexical" in benchmark["metrics_by_strategy"]
    assert "hybrid" in benchmark["metrics_by_strategy"]
    assert "failure_taxonomy" in benchmark
