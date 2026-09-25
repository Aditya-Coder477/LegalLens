"""
pipeline/evaluation/performance_evaluator.py
============================================
Performance & Latency benchmarking engine for LegalLens Phase 8.
Measures latency distribution (mean, median, P95, P99) across all pipeline stages:
- Query Processing
- Lexical Search
- Semantic Search
- Hybrid Fusion
- Context Expansion
- Reranking
- LLM Generation
- Citation Verification
- Grounding / Guardrails
- End-to-End
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from pipeline.legal_ai.service import LegalAIService
from pipeline.retrieval.retriever import HybridRetriever
from pipeline.safety.service import SafetyService

from .config import EvaluationConfig, get_evaluation_config
from .metrics import compute_latency_stats
from .models import EvaluationCase

logger = logging.getLogger("legallens.evaluation.performance")


class PerformanceEvaluator:
    """
    Benchmarks system latency across components and end-to-end execution.
    """

    def __init__(
        self,
        retriever: Optional[HybridRetriever] = None,
        ai_service: Optional[LegalAIService] = None,
        safety_service: Optional[SafetyService] = None,
        config: Optional[EvaluationConfig] = None,
    ):
        self.config = config or get_evaluation_config()
        self.retriever = retriever or HybridRetriever()
        self.ai_service = ai_service or LegalAIService()
        self.safety_service = safety_service or SafetyService()

    def benchmark_pipeline(self, cases: List[EvaluationCase], iterations: int = 1) -> Dict[str, Any]:
        """
        Run latency benchmark over a sample of cases.
        """
        retrieval_latencies: List[float] = []
        lexical_latencies: List[float] = []
        semantic_latencies: List[float] = []
        reasoning_latencies: List[float] = []
        citation_latencies: List[float] = []
        safety_latencies: List[float] = []
        e2e_latencies: List[float] = []

        logger.info(f"Running performance benchmark across {len(cases)} queries ({iterations} iters)...")

        for _ in range(iterations):
            for case in cases:
                t_e2e_0 = time.time()

                # 1. Lexical Latency
                t0 = time.time()
                _ = self.retriever.lexical_retriever.retrieve(case.query, top_k=10)
                lexical_latencies.append((time.time() - t0) * 1000.0)

                # 2. Semantic Latency
                t0 = time.time()
                _ = self.retriever.semantic_retriever.retrieve(case.query, top_k=10)
                semantic_latencies.append((time.time() - t0) * 1000.0)

                # 3. Full Hybrid Retrieval Latency
                t0 = time.time()
                bundle = self.retriever.retrieve(case.query, top_k=10)
                retrieval_latencies.append((time.time() - t0) * 1000.0)

                # 4. Legal AI Generation Latency
                t0 = time.time()
                ai_resp = self.ai_service.execute_task(case.query)
                reasoning_latencies.append((time.time() - t0) * 1000.0)

                # 5. Citation Verification Latency
                t0 = time.time()
                if ai_resp.evidence_refs:
                    for cit in ai_resp.evidence_refs[:3]:
                        _ = self.safety_service.citation_verifier.verify_citation(cit)
                citation_latencies.append((time.time() - t0) * 1000.0)

                # 6. Safety Audit Latency
                t0 = time.time()
                _ = self.safety_service.audit_response(ai_resp)
                safety_latencies.append((time.time() - t0) * 1000.0)

                # Total E2E Latency
                e2e_latencies.append((time.time() - t_e2e_0) * 1000.0)

        stats = {
            "retrieval": compute_latency_stats(retrieval_latencies),
            "lexical": compute_latency_stats(lexical_latencies),
            "semantic": compute_latency_stats(semantic_latencies),
            "reasoning": compute_latency_stats(reasoning_latencies),
            "citation_verification": compute_latency_stats(citation_latencies),
            "safety_audit": compute_latency_stats(safety_latencies),
            "end_to_end": compute_latency_stats(e2e_latencies),
        }

        # Check SLAs
        sla_checks = {
            "retrieval_sla_met": stats["retrieval"]["p95"] <= self.config.max_retrieval_latency_ms,
            "citation_sla_met": stats["citation_verification"]["p95"] <= self.config.max_citation_verification_latency_ms,
            "e2e_sla_met": stats["end_to_end"]["p95"] <= self.config.max_end_to_end_latency_ms,
        }

        return {
            "sample_size": len(cases) * iterations,
            "latency_stats": stats,
            "sla_checks": sla_checks,
        }
