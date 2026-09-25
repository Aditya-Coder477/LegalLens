"""
tests/evaluation/test_quality_gate.py
=====================================
Tests for QualityGate threshold evaluations and outcomes (PASS, REVIEW, FAIL).
"""

import pytest

from pipeline.evaluation.config import EvaluationConfig
from pipeline.evaluation.models import QualityGateStatus
from pipeline.evaluation.quality_gate import QualityGate


def test_quality_gate_pass():
    config = EvaluationConfig(
        min_recall_at_10=0.80,
        min_mrr=0.60,
        max_unsupported_claim_rate=0.05,
        min_citation_validity_rate=0.95,
        max_critical_security_findings=0,
    )
    qg = QualityGate(config=config)

    result = qg.evaluate(
        retrieval_metrics={"recall@10": 0.85, "mrr": 0.70, "ndcg@10": 0.75},
        grounding_metrics={"unsupported_claim_rate": 0.02, "contradiction_rate": 0.0},
        citation_metrics={"overall_citation_validity_rate": 0.98},
        security_findings=[],
        performance_stats={"latency_stats": {"end_to_end": {"p95": 800.0}}},
    )

    assert result.status == QualityGateStatus.PASS
    assert result.passed is True
    assert len(result.blockers) == 0


def test_quality_gate_fail_on_critical_security():
    qg = QualityGate()
    result = qg.evaluate(
        retrieval_metrics={"recall@10": 0.90, "mrr": 0.80},
        grounding_metrics={"unsupported_claim_rate": 0.01, "contradiction_rate": 0.0},
        citation_metrics={"overall_citation_validity_rate": 0.99},
        security_findings=[{"severity": "CRITICAL", "title": "Secret Leaked"}],
        performance_stats={"latency_stats": {"end_to_end": {"p95": 500.0}}},
    )

    assert result.status == QualityGateStatus.FAIL
    assert result.passed is False
    assert any("CRITICAL" in b for b in result.blockers)


def test_quality_gate_fail_on_low_retrieval():
    qg = QualityGate()
    result = qg.evaluate(
        retrieval_metrics={"recall@10": 0.40, "mrr": 0.30},
        grounding_metrics={"unsupported_claim_rate": 0.01, "contradiction_rate": 0.0},
        citation_metrics={"overall_citation_validity_rate": 0.99},
        security_findings=[],
        performance_stats={"latency_stats": {"end_to_end": {"p95": 500.0}}},
    )

    assert result.status == QualityGateStatus.FAIL
    assert any("Retrieval" in b for b in result.blockers)
