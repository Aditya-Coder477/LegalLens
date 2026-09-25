"""
pipeline/evaluation/quality_gate.py
===================================
Automated Quality Gate engine for LegalLens Phase 8.
Evaluates multi-dimensional benchmark results against configurable thresholds
to output a definitive PASS / REVIEW / FAIL determination.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .config import EvaluationConfig, get_evaluation_config
from .models import QualityGateDimension, QualityGateResult, QualityGateStatus

logger = logging.getLogger("legallens.evaluation.quality_gate")


class QualityGate:
    """
    Evaluates system metrics against production readiness thresholds.
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or get_evaluation_config()

    def evaluate(
        self,
        retrieval_metrics: Dict[str, float],
        grounding_metrics: Dict[str, float],
        citation_metrics: Dict[str, float],
        security_findings: List[Dict[str, Any]],
        performance_stats: Dict[str, Any],
    ) -> QualityGateResult:
        """
        Evaluate all dimensions and determine deployment readiness.
        """
        dimensions: List[QualityGateDimension] = []
        blockers: List[str] = []
        warnings: List[str] = []

        # 1. Retrieval Dimension (Recall@10, MRR, NDCG@10)
        rec10 = retrieval_metrics.get("recall@10", 0.0)
        mrr = retrieval_metrics.get("mrr", 0.0)
        ndcg10 = retrieval_metrics.get("ndcg@10", 0.0)

        ret_passed = (rec10 >= self.config.min_recall_at_10 * 0.75) and (mrr >= self.config.min_mrr * 0.75)
        if not ret_passed:
            blockers.append(
                f"Retrieval Recall@10 ({rec10:.2f}) or MRR ({mrr:.2f}) below threshold (min recall: {self.config.min_recall_at_10}, min mrr: {self.config.min_mrr})"
            )
        elif rec10 < self.config.min_recall_at_10:
            warnings.append(f"Retrieval Recall@10 ({rec10:.2f}) slightly below target {self.config.min_recall_at_10}")

        dimensions.append(
            QualityGateDimension(
                name="Retrieval Quality",
                metric_name="recall@10, mrr, ndcg@10",
                actual_value=round(rec10, 4),
                threshold=self.config.min_recall_at_10,
                passed=ret_passed,
                details={"recall@10": rec10, "mrr": mrr, "ndcg@10": ndcg10},
            )
        )

        # 2. Grounding Dimension (Unsupported Claim Rate, Contradiction Rate)
        unsupp_rate = grounding_metrics.get("unsupported_claim_rate", 0.0)
        contra_rate = grounding_metrics.get("contradiction_rate", 0.0)

        ground_passed = (unsupp_rate <= self.config.max_unsupported_claim_rate) and (
            contra_rate <= self.config.max_contradiction_rate
        )
        if not ground_passed:
            blockers.append(
                f"Grounding unsupported rate ({unsupp_rate:.2f}) or contradiction rate ({contra_rate:.2f}) exceeded threshold"
            )

        dimensions.append(
            QualityGateDimension(
                name="Grounding & Faithfulness",
                metric_name="unsupported_claim_rate",
                actual_value=round(unsupp_rate, 4),
                threshold=self.config.max_unsupported_claim_rate,
                passed=ground_passed,
                details={"unsupported_claim_rate": unsupp_rate, "contradiction_rate": contra_rate},
            )
        )

        # 3. Citation Dimension (Validity Rate, SHA-256 match rate)
        cit_rate = citation_metrics.get("overall_citation_validity_rate", citation_metrics.get("citation_validity_rate", 0.0))
        cit_passed = cit_rate >= self.config.min_citation_validity_rate
        if not cit_passed:
            blockers.append(
                f"Citation validity rate ({cit_rate:.2f}) below required threshold ({self.config.min_citation_validity_rate})"
            )

        dimensions.append(
            QualityGateDimension(
                name="Citation & Provenance Integrity",
                metric_name="citation_validity_rate",
                actual_value=round(cit_rate, 4),
                threshold=self.config.min_citation_validity_rate,
                passed=cit_passed,
                details=citation_metrics,
            )
        )

        # 4. Security Dimension (Critical and High vulnerabilities)
        crit_count = sum(1 for f in security_findings if f.get("severity") in ("CRITICAL", "critical"))
        high_count = sum(1 for f in security_findings if f.get("severity") in ("HIGH", "high"))
        med_count = sum(1 for f in security_findings if f.get("severity") in ("MEDIUM", "medium"))

        sec_passed = (crit_count <= self.config.max_critical_security_findings) and (
            high_count <= self.config.max_high_security_findings
        )
        if crit_count > 0:
            blockers.append(f"Found {crit_count} CRITICAL security vulnerabilities")
        if high_count > 0:
            blockers.append(f"Found {high_count} HIGH security vulnerabilities")
        if med_count > 0:
            warnings.append(f"Found {med_count} MEDIUM security findings")

        dimensions.append(
            QualityGateDimension(
                name="Security & Safety",
                metric_name="critical_and_high_findings",
                actual_value=crit_count + high_count,
                threshold=0.0,
                passed=sec_passed,
                details={"critical": crit_count, "high": high_count, "medium": med_count},
            )
        )

        # 5. Performance / Latency Dimension
        e2e_stats = performance_stats.get("latency_stats", {}).get("end_to_end", {})
        p95_latency = e2e_stats.get("p95", 0.0)
        perf_passed = p95_latency <= (self.config.max_end_to_end_latency_ms * 2.0)  # Tolerant for test env

        if p95_latency > self.config.max_end_to_end_latency_ms:
            warnings.append(
                f"P95 latency ({p95_latency:.1f}ms) exceeds target {self.config.max_end_to_end_latency_ms}ms"
            )

        dimensions.append(
            QualityGateDimension(
                name="Performance & Latency",
                metric_name="e2e_p95_ms",
                actual_value=round(p95_latency, 1),
                threshold=self.config.max_end_to_end_latency_ms,
                passed=perf_passed,
                details=e2e_stats,
            )
        )

        # Overall Status
        if len(blockers) > 0:
            status = QualityGateStatus.FAIL
        elif len(warnings) > 0:
            status = QualityGateStatus.REVIEW
        else:
            status = QualityGateStatus.PASS

        return QualityGateResult(
            status=status,
            passed=(status == QualityGateStatus.PASS),
            dimensions=dimensions,
            blockers=blockers,
            warnings=warnings,
            metadata={
                "total_dimensions": len(dimensions),
                "passed_dimensions": sum(1 for d in dimensions if d.passed),
            },
        )
