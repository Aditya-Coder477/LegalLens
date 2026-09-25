"""
pipeline/evaluation/citation_evaluator.py
=========================================
Citation evaluation module for LegalLens Phase 8.
Evaluates citation validity, precision, recall, SHA-256 hash match rate,
and detects fabricated or dead citations using Phase 7 CitationVerifier.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from pipeline.knowledge_base.config import get_kb_config
from pipeline.knowledge_base.db import DatabaseManager
from pipeline.safety.citation_verifier import CitationVerifier
from pipeline.safety.config import get_safety_config
from pipeline.safety.models import CitationVerificationResult, CitationVerificationStatus

from .config import EvaluationConfig, get_evaluation_config
from .metrics import compute_citation_metrics
from .models import EvaluationCase, EvaluationResult, EvaluationStatus

logger = logging.getLogger("legallens.evaluation.citations")


class CitationEvaluator:
    """
    Evaluates citation resolution and provenance integrity.
    """

    def __init__(
        self,
        citation_verifier: Optional[CitationVerifier] = None,
        db_manager: Optional[DatabaseManager] = None,
        config: Optional[EvaluationConfig] = None,
    ):
        self.config = config or get_evaluation_config()
        self.db = db_manager or DatabaseManager(get_kb_config().database_url)
        self.citation_verifier = citation_verifier or CitationVerifier(
            db_manager=self.db,
            config=get_safety_config(),
        )

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        """
        Evaluate citations for a case.
        """
        t0 = time.time()
        citations_to_check: List[str] = []

        # Ground truth expected citations
        if case.expected_citations:
            citations_to_check.extend(case.expected_citations)
        elif case.expected_sections:
            citations_to_check.extend(case.expected_sections)
        elif case.expected_chunk_ids:
            citations_to_check.extend(case.expected_chunk_ids)

        if not citations_to_check and case.expected_documents:
            citations_to_check.extend(case.expected_documents)

        # Also extract citations if query or answer contains mentions
        extracted = self.citation_verifier.extract_citations_from_text(case.query)
        if case.expected_answer:
            extracted.extend(self.citation_verifier.extract_citations_from_text(case.expected_answer))
        citations_to_check.extend(extracted)
        citations_to_check = list(set(citations_to_check))

        valid_count = 0
        sha_matches = 0
        status_results: List[CitationVerificationResult] = []

        for cit in citations_to_check:
            res = self.citation_verifier.verify_citation(cit)
            status_results.append(res)
            if res.is_valid:
                valid_count += 1
            if res.hash_matched:
                sha_matches += 1

        total = len(citations_to_check)
        validity_rate = valid_count / total if total > 0 else 1.0
        sha_rate = sha_matches / total if total > 0 else 1.0

        latency_ms = (time.time() - t0) * 1000.0

        failures = []
        if validity_rate < self.config.min_citation_validity_rate and total > 0:
            failures.append(f"Citation validity ({validity_rate:.2f}) < required ({self.config.min_citation_validity_rate})")

        metrics = {
            "citation_validity_rate": round(validity_rate, 4),
            "sha256_match_rate": round(sha_rate, 4),
            "citations_evaluated": total,
            "valid_citations": valid_count,
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
                "citations": citations_to_check,
                "verified_statuses": [r.status.value for r in status_results],
            },
        )

    def evaluate_batch(self, cases: List[EvaluationCase]) -> Dict[str, Any]:
        """
        Evaluate a batch of citation cases.
        """
        results: List[EvaluationResult] = []
        total_eval = 0
        total_valid = 0
        total_sha = 0

        for case in cases:
            res = self.evaluate_case(case)
            results.append(res)
            total_eval += res.metrics.get("citations_evaluated", 0)
            total_valid += res.metrics.get("valid_citations", 0)
            total_sha += int(res.metrics.get("sha256_match_rate", 0) * res.metrics.get("citations_evaluated", 0))

        overall_validity = total_valid / total_eval if total_eval > 0 else 1.0
        overall_sha = total_sha / total_eval if total_eval > 0 else 1.0
        pass_count = sum(1 for r in results if r.status == EvaluationStatus.PASS)

        return {
            "total_cases": len(cases),
            "passed": pass_count,
            "pass_rate": round(pass_count / max(len(cases), 1), 4),
            "metrics": {
                "overall_citation_validity_rate": round(overall_validity, 4),
                "overall_sha256_match_rate": round(overall_sha, 4),
                "total_citations_evaluated": total_eval,
                "total_valid_citations": total_valid,
            },
            "results": [r.to_dict() for r in results],
        }
