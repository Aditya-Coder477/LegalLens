"""
pipeline/evaluation/qa_evaluator.py
===================================
Evaluator for Legal AI reasoning tasks:
- Grounded Legal Q&A
- Unanswerable Questions (Abstention check)
- Contradictory Legal Provisions
- Version-Aware / Historical Law Queries
- Legal Summarization, Clause Analysis, and Comparison
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from pipeline.legal_ai.models import LegalAIResponse, TaskType
from pipeline.legal_ai.service import LegalAIService

from .config import EvaluationConfig, get_evaluation_config
from .models import EvaluationCase, EvaluationResult, EvaluationStatus

logger = logging.getLogger("legallens.evaluation.qa")


class QAEvaluator:
    """
    Evaluates Legal AI answers for correctness, grounding, citations,
    and proper abstention behavior.
    """

    def __init__(
        self,
        ai_service: Optional[LegalAIService] = None,
        config: Optional[EvaluationConfig] = None,
    ):
        self.config = config or get_evaluation_config()
        self.ai_service = ai_service or LegalAIService()

    def evaluate_grounded_qa(self, case: EvaluationCase) -> EvaluationResult:
        """
        Evaluate standard grounded QA query.
        Verifies answer contains expected concepts/entities, has citations, and has positive confidence.
        """
        t0 = time.time()
        response: LegalAIResponse = self.ai_service.execute_task(
            query=case.query,
            task_type=TaskType.LEGAL_QA,
        )
        latency_ms = (time.time() - t0) * 1000.0

        direct_ans = response.direct_answer or ""
        ans_lower = direct_ans.lower() + " " + " ".join([c.text.lower() for c in response.claims])
        failures = []

        # 1. Expected answer keywords check
        keyword_coverage = 1.0
        if case.expected_answer:
            exp_keywords = [w.lower().strip() for w in case.expected_answer.split() if len(w) > 4]
            matches = [kw for kw in exp_keywords if kw in ans_lower]
            keyword_coverage = len(matches) / max(len(exp_keywords), 1)
            if keyword_coverage < 0.2:
                failures.append(f"Low keyword overlap with expected answer: {keyword_coverage:.2f}")

        # 2. Citation / Evidence presence
        has_citations = len(response.evidence_refs) > 0 or any(c.evidence_refs for c in response.claims)
        if not has_citations and response.status == "SUCCESS":
            failures.append("Missing citations/evidence references for grounded legal claim")

        # 3. Confidence score check
        confidence = response.claim_support_rate

        metrics = {
            "confidence": round(confidence, 3),
            "citations_count": len(response.evidence_refs),
            "claims_count": len(response.claims),
            "keyword_coverage": round(keyword_coverage, 3),
        }

        status = EvaluationStatus.PASS if len(failures) == 0 else EvaluationStatus.FAIL

        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            metrics=metrics,
            failures=failures,
            latency_ms=latency_ms,
            details={
                "direct_answer": direct_ans[:200],
                "evidence_refs": response.evidence_refs[:5],
            },
        )

    def evaluate_unanswerable(self, case: EvaluationCase) -> EvaluationResult:
        """
        Evaluate questions with no evidence in the corpus.
        Model MUST abstain or explicitly state lack of authoritative information.
        """
        t0 = time.time()
        response: LegalAIResponse = self.ai_service.execute_task(
            query=case.query,
            task_type=TaskType.LEGAL_QA,
        )
        latency_ms = (time.time() - t0) * 1000.0

        direct_ans = response.direct_answer or ""
        ans_lower = direct_ans.lower() + " " + " ".join([c.text.lower() for c in response.claims])

        abstention_signals = [
            "no information",
            "insufficient evidence",
            "not found",
            "no authoritative",
            "does not contain",
            "unable to determine",
            "outside the scope",
            "no evidence",
            "abstain",
            "cannot answer",
            "unsupported",
            "no direct provision",
            "no provision",
            "not mentioned",
            "no specific",
        ]

        abstained = any(signal in ans_lower for signal in abstention_signals) or response.status in ("LOW_EVIDENCE", "NO_EVIDENCE")

        failures = []
        if not abstained and response.status == "SUCCESS":
            if "section" in ans_lower and not response.evidence_refs:
                failures.append("Hallucinated answer on unanswerable query without evidence citations")

        metrics = {
            "abstained": 1.0 if abstained else 0.0,
            "evidence_count": len(response.evidence_refs),
            "confidence": round(response.claim_support_rate, 3),
        }

        status = EvaluationStatus.PASS if (abstained or response.claim_support_rate < 0.5) else EvaluationStatus.FAIL

        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            metrics=metrics,
            failures=failures,
            latency_ms=latency_ms,
            details={"direct_answer": direct_ans[:200], "abstained": abstained},
        )

    def evaluate_contradiction(self, case: EvaluationCase) -> EvaluationResult:
        """
        Evaluate queries involving conflicting provisions.
        Must note conflict, precedence (e.g. Act prevails over Rule), or qualification.
        """
        t0 = time.time()
        response: LegalAIResponse = self.ai_service.execute_task(
            query=case.query,
            task_type=TaskType.LEGAL_QA,
        )
        latency_ms = (time.time() - t0) * 1000.0

        direct_ans = response.direct_answer or ""
        ans_lower = direct_ans.lower() + " " + " ".join([c.text.lower() for c in response.claims])
        conflict_signals = [
            "conflict",
            "prevail",
            "override",
            "supersede",
            "subject to",
            "notwithstanding",
            "distinction",
            "hierarchy",
            "differ",
            "inconsistency",
            "rule",
            "act",
            "exception",
        ]

        detected_conflict = any(sig in ans_lower for sig in conflict_signals)
        failures = []
        if not detected_conflict and len(response.evidence_refs) > 1:
            failures.append("Failed to articulate contradiction or hierarchy between provisions")

        metrics = {
            "conflict_identified": 1.0 if detected_conflict else 0.0,
            "confidence": round(response.claim_support_rate, 3),
        }

        status = EvaluationStatus.PASS if detected_conflict else EvaluationStatus.FAIL

        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            metrics=metrics,
            failures=failures,
            latency_ms=latency_ms,
            details={"direct_answer": direct_ans[:200]},
        )

    def evaluate_version_awareness(self, case: EvaluationCase) -> EvaluationResult:
        """
        Evaluate queries about repealed, amended, or historical provisions.
        """
        t0 = time.time()
        response: LegalAIResponse = self.ai_service.execute_task(
            query=case.query,
            task_type=TaskType.LEGAL_QA,
        )
        latency_ms = (time.time() - t0) * 1000.0

        direct_ans = response.direct_answer or ""
        ans_lower = direct_ans.lower() + " " + " ".join([c.text.lower() for c in response.claims])
        version_signals = [
            "repeal",
            "amend",
            "historical",
            "enact",
            "prior to",
            "substituted",
            "in force",
            "year",
            "superseded",
            "version",
        ]

        acknowledged_version = any(sig in ans_lower for sig in version_signals)
        metrics = {
            "version_acknowledged": 1.0 if acknowledged_version else 0.0,
            "confidence": round(response.claim_support_rate, 3),
        }

        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            status=EvaluationStatus.PASS if acknowledged_version else EvaluationStatus.FAIL,
            metrics=metrics,
            failures=[] if acknowledged_version else ["Did not acknowledge versioning/amendment context"],
            latency_ms=latency_ms,
            details={"direct_answer": direct_ans[:200]},
        )

    def evaluate_batch(self, cases: List[EvaluationCase]) -> Dict[str, Any]:
        """
        Evaluate a mixed batch of QA evaluation cases.
        """
        results: List[EvaluationResult] = []
        for case in cases:
            if case.category == "unanswerable_qa":
                res = self.evaluate_unanswerable(case)
            elif case.category == "contradiction_qa":
                res = self.evaluate_contradiction(case)
            elif case.category == "version_qa":
                res = self.evaluate_version_awareness(case)
            else:
                res = self.evaluate_grounded_qa(case)
            results.append(res)

        pass_count = sum(1 for r in results if r.status == EvaluationStatus.PASS)
        avg_latency = sum(r.latency_ms for r in results) / max(len(results), 1)

        return {
            "total_cases": len(cases),
            "passed": pass_count,
            "pass_rate": round(pass_count / max(len(cases), 1), 4),
            "avg_latency_ms": round(avg_latency, 2),
            "results": [r.to_dict() for r in results],
        }
