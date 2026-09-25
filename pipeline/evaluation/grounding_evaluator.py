"""
pipeline/evaluation/grounding_evaluator.py
=========================================
Grounding evaluation module for LegalLens Phase 8.
Evaluates claim-level entailment, unsupported claims, and contradiction rates
using Phase 7 GroundingEngine.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from pipeline.legal_ai.models import Claim
from pipeline.retrieval.models import RetrievedEvidence
from pipeline.retrieval.retriever import HybridRetriever
from pipeline.safety.config import get_safety_config
from pipeline.safety.grounding_engine import GroundingEngine
from pipeline.safety.models import ClaimVerificationResult, EntailmentStatus

from .config import EvaluationConfig, get_evaluation_config
from .metrics import compute_grounding_metrics
from .models import EvaluationCase, EvaluationResult, EvaluationStatus

logger = logging.getLogger("legallens.evaluation.grounding")


class GroundingEvaluator:
    """
    Evaluates grounding quality, claim support rates, and hallucination flags.
    """

    def __init__(
        self,
        grounding_engine: Optional[GroundingEngine] = None,
        retriever: Optional[HybridRetriever] = None,
        config: Optional[EvaluationConfig] = None,
    ):
        self.config = config or get_evaluation_config()
        self.retriever = retriever or HybridRetriever()
        self.grounding_engine = grounding_engine or GroundingEngine(get_safety_config())

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        """
        Evaluate claim grounding for an evaluation case.
        """
        t0 = time.time()

        # Gather relevant evidence from retriever or DB
        bundle = self.retriever.retrieve(query=case.query, top_k=5)
        evidence_map = {item.chunk_id: item for item in bundle.primary_evidence}

        # Build mock or test claims from case expected answer/assertions
        claims_to_test: List[Claim] = []
        if case.expected_answer:
            claims_to_test.append(
                Claim(
                    text=case.expected_answer,
                    citations=list(case.expected_chunk_ids) or [item.chunk_id for item in bundle.primary_evidence[:1]],
                    confidence=0.9,
                )
            )

        if not claims_to_test and bundle.primary_evidence:
            ev = bundle.primary_evidence[0]
            claims_to_test.append(
                Claim(
                    text=ev.text[:120],
                    evidence_refs=[ev.chunk_id],
                )
            )

        verification_results: List[ClaimVerificationResult] = []
        for i, cl in enumerate(claims_to_test):
            ev_refs = getattr(cl, "evidence_refs", getattr(cl, "citations", []))
            res = self.grounding_engine.verify_claim(
                claim_text=cl.text,
                claim_id=f"cl-{i+1}",
                cited_evidence_ids=ev_refs,
                evidence_map=evidence_map,
            )
            verification_results.append(res)

        status_strings = [r.status.value for r in verification_results]
        g_metrics = compute_grounding_metrics(status_strings)

        latency_ms = (time.time() - t0) * 1000.0

        failures = []
        if g_metrics["unsupported_claim_rate"] > self.config.max_unsupported_claim_rate:
            failures.append(
                f"Unsupported claim rate ({g_metrics['unsupported_claim_rate']:.2f}) exceeds threshold ({self.config.max_unsupported_claim_rate})"
            )
        if g_metrics["contradiction_rate"] > self.config.max_contradiction_rate:
            failures.append(
                f"Contradiction rate ({g_metrics['contradiction_rate']:.2f}) exceeds threshold ({self.config.max_contradiction_rate})"
            )

        status = EvaluationStatus.PASS if len(failures) == 0 else EvaluationStatus.FAIL

        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            metrics=g_metrics,
            failures=failures,
            latency_ms=latency_ms,
            details={
                "claims_evaluated": len(claims_to_test),
                "entailment_statuses": status_strings,
            },
        )

    def evaluate_batch(self, cases: List[EvaluationCase]) -> Dict[str, Any]:
        """
        Evaluate a batch of grounding evaluation cases.
        """
        results: List[EvaluationResult] = []
        all_statuses: List[str] = []

        for case in cases:
            res = self.evaluate_case(case)
            results.append(res)
            all_statuses.extend(res.details.get("entailment_statuses", []))

        agg_metrics = compute_grounding_metrics(all_statuses)
        pass_count = sum(1 for r in results if r.status == EvaluationStatus.PASS)

        return {
            "total_cases": len(cases),
            "passed": pass_count,
            "pass_rate": round(pass_count / max(len(cases), 1), 4),
            "metrics": agg_metrics,
            "results": [r.to_dict() for r in results],
        }
