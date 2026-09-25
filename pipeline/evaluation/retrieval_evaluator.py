"""
pipeline/evaluation/retrieval_evaluator.py
==========================================
Comprehensive IR benchmark engine for LegalLens.
Evaluates 5 retrieval configurations:
1. Lexical (FTS/BM25)
2. Semantic (Vector/Embeddings)
3. Hybrid (RRF Fusion)
4. Hybrid + Rerank
5. Hybrid + Expansion

Computes Recall@K, Precision@K, HitRate@K, MRR, NDCG@K for K in [1, 3, 5, 10, 20],
and categorizes retrieval failures into a formal taxonomy.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pipeline.retrieval.config import get_retrieval_config
from pipeline.retrieval.models import EvidenceBundle, RetrievedEvidence
from pipeline.retrieval.query_processor import QueryProcessor
from pipeline.retrieval.reranker import LocalTermReranker
from pipeline.retrieval.retriever import HybridRetriever

from .config import EvaluationConfig, get_evaluation_config
from .metrics import hit_rate_at_k, ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from .models import EvaluationCase, EvaluationResult, EvaluationStatus

logger = logging.getLogger("legallens.evaluation.retrieval")

# Standard K thresholds
EVAL_K_VALUES = [1, 3, 5, 10, 20]


def is_chunk_relevant(chunk_id: str, case: EvaluationCase) -> bool:
    """
    Check if a chunk matches ground truth chunk IDs, sections, or documents.
    """
    if chunk_id in case.expected_chunk_ids:
        return True
    for exp_id in case.expected_chunk_ids:
        if chunk_id.startswith(exp_id) or exp_id.startswith(chunk_id):
            return True
    for sec in case.expected_sections:
        if sec == chunk_id:
            return True
        if "-SEC-" in sec:
            doc_id, sec_num = sec.split("-SEC-", 1)
            if chunk_id.startswith(doc_id):
                sec_clean = sec_num.strip()
                if sec_clean.isdigit():
                    patterns = [f"-S{int(sec_clean):02d}", f"-S{sec_clean}"]
                else:
                    patterns = [f"-S{sec_clean}"]
                for p in patterns:
                    if chunk_id.endswith(p) or f"{p}-" in chunk_id or f"{p}_" in chunk_id:
                        return True
        elif sec in chunk_id:
            return True
    for doc in getattr(case, "expected_document_ids", []) + getattr(case, "expected_documents", []):
        if chunk_id.startswith(doc):
            return True
    return False


def get_chunk_relevance_grade(chunk_id: str, case: EvaluationCase) -> int:
    """
    Get graded relevance score (0..3) for NDCG.
    """
    if case.relevance_scores and chunk_id in case.relevance_scores:
        return case.relevance_scores[chunk_id]
    if chunk_id in case.expected_chunk_ids:
        return 3
    for exp_id in case.expected_chunk_ids:
        if chunk_id.startswith(exp_id) or exp_id.startswith(chunk_id):
            return 3
    for sec in case.expected_sections:
        if sec in chunk_id:
            return 2
    for doc in getattr(case, "expected_document_ids", []) + getattr(case, "expected_documents", []):
        if chunk_id.startswith(doc):
            return 2
    return 0


class RetrievalEvaluator:
    """
    Evaluates IR quality across multiple retrieval strategies and failure taxonomy.
    """

    def __init__(
        self,
        retriever: Optional[HybridRetriever] = None,
        config: Optional[EvaluationConfig] = None,
    ):
        self.config = config or get_evaluation_config()
        self.retriever = retriever or HybridRetriever()
        self.query_processor = QueryProcessor()
        self.reranker = LocalTermReranker()

    def run_strategy(
        self,
        strategy: str,
        query: str,
        top_k: int = 20,
    ) -> List[RetrievedEvidence]:
        """
        Execute a specific retrieval strategy.
        Strategies:
        - 'lexical': lexical only
        - 'semantic': semantic vector only
        - 'hybrid': lexical + semantic fused via RRF
        - 'hybrid_rerank': hybrid + local term reranker
        - 'hybrid_expansion': expanded query + hybrid
        """
        if strategy == "lexical":
            return self.retriever.lexical_retriever.retrieve(query=query, top_k=top_k)

        elif strategy == "semantic":
            return self.retriever.semantic_retriever.retrieve(query=query, top_k=top_k)

        elif strategy == "hybrid":
            lex = self.retriever.lexical_retriever.retrieve(query=query, top_k=top_k * 2)
            sem = self.retriever.semantic_retriever.retrieve(query=query, top_k=top_k * 2)
            fused = self.retriever.fusion_engine.fuse(lex, sem, top_k=top_k)
            return self.retriever.deduplicator.deduplicate(fused)[:top_k]

        elif strategy == "hybrid_rerank":
            bundle = self.retriever.retrieve(query=query, top_k=top_k, rerank=True)
            return bundle.primary_evidence

        elif strategy == "hybrid_expansion":
            # Expand query with legal aliases/entities
            exp_query = self.query_processor.expand_for_retrieval(query)
            bundle = self.retriever.retrieve(query=exp_query, top_k=top_k, rerank=False)
            return bundle.primary_evidence

        else:
            bundle = self.retriever.retrieve(query=query, top_k=top_k)
            return bundle.primary_evidence

    def evaluate_case(
        self,
        case: EvaluationCase,
        strategy: str = "hybrid",
        top_k: int = 20,
    ) -> EvaluationResult:
        """
        Evaluate a single case under a chosen strategy.
        """
        t0 = time.time()
        retrieved_items = self.run_strategy(strategy, case.query, top_k=top_k)
        latency_ms = (time.time() - t0) * 1000.0

        retrieved_ids = [item.chunk_id for item in retrieved_items]

        # Target relevant IDs
        relevant_targets = set(case.expected_chunk_ids)
        for item in retrieved_items:
            if is_chunk_relevant(item.chunk_id, case):
                relevant_targets.add(item.chunk_id)

        # Graded relevance vector
        graded_rel = [get_chunk_relevance_grade(cid, case) for cid in retrieved_ids]

        # Compute metrics
        metrics: Dict[str, float] = {}
        for k in EVAL_K_VALUES:
            metrics[f"recall@{k}"] = recall_at_k(retrieved_ids, relevant_targets, k=k)
            metrics[f"precision@{k}"] = precision_at_k(retrieved_ids, relevant_targets, k=k)
            metrics[f"hit_rate@{k}"] = hit_rate_at_k(retrieved_ids, relevant_targets, k=k)

        metrics["mrr"] = reciprocal_rank(retrieved_ids, relevant_targets)
        metrics["ndcg@10"] = ndcg_at_k(graded_rel, k=10)

        # Check failures
        failures = []
        if metrics["recall@10"] < 0.5 and relevant_targets:
            failures.append(f"Low Recall@10: {metrics['recall@10']:.2f} for query: {case.query}")

        status = EvaluationStatus.PASS if metrics.get("hit_rate@10", 0) > 0 else EvaluationStatus.FAIL

        return EvaluationResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            metrics=metrics,
            failures=failures,
            latency_ms=latency_ms,
            details={
                "strategy": strategy,
                "retrieved_chunk_ids": retrieved_ids[:10],
                "expected_chunk_ids": list(case.expected_chunk_ids),
                "expected_sections": list(case.expected_sections),
            },
        )

    def diagnose_failure(
        self,
        case: EvaluationCase,
        retrieved_ids: List[str],
        lex_ids: List[str],
        sem_ids: List[str],
    ) -> Optional[str]:
        """
        Classify retrieval failure into the taxonomy.
        """
        hit_any = any(is_chunk_relevant(cid, case) for cid in retrieved_ids[:10])
        if hit_any:
            return None

        # Check if lexical missed but semantic found
        lex_hit = any(is_chunk_relevant(cid, case) for cid in lex_ids[:10])
        sem_hit = any(is_chunk_relevant(cid, case) for cid in sem_ids[:10])

        if sem_hit and not lex_hit:
            return "vocabulary_mismatch"
        if lex_hit and not sem_hit:
            return "semantic_drift"
        if any(is_chunk_relevant(cid, case) for cid in retrieved_ids[10:]):
            return "low_similarity_rank"

        # Check if KB even has relevant documents
        doc_found = False
        try:
            from pipeline.knowledge_base.db_models import KBChunkTable
            with self.retriever.db.session_scope() as session:
                for exp_doc in case.expected_documents:
                    cnt = session.query(KBChunkTable).filter_by(document_id=exp_doc).count()
                    if cnt > 0:
                        doc_found = True
                        break
        except Exception:
            doc_found = True
        if not doc_found and case.expected_documents:
            return "missing_chunk_in_kb"

        return "chunk_boundary_cutoff"

    def evaluate_benchmark(
        self,
        cases: List[EvaluationCase],
        strategies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate full test suite across all 5 retrieval strategies.
        """
        if not strategies:
            strategies = ["lexical", "semantic", "hybrid", "hybrid_rerank", "hybrid_expansion"]

        strategy_results: Dict[str, List[EvaluationResult]] = {}
        strategy_metrics: Dict[str, Dict[str, float]] = {}
        failure_taxonomy: Dict[str, int] = defaultdict(int)

        logger.info(f"Starting IR benchmark across {len(cases)} cases and {len(strategies)} strategies.")

        for strat in strategies:
            strat_res = []
            for case in cases:
                res = self.evaluate_case(case, strategy=strat, top_k=20)
                strat_res.append(res)
            strategy_results[strat] = strat_res

            # Aggregate metrics for this strategy
            agg: Dict[str, float] = {}
            if strat_res:
                for metric_key in strat_res[0].metrics.keys():
                    vals = [r.metrics[metric_key] for r in strat_res]
                    agg[metric_key] = round(sum(vals) / len(vals), 4)
                agg["avg_latency_ms"] = round(sum(r.latency_ms for r in strat_res) / len(strat_res), 2)
            strategy_metrics[strat] = agg

        # Failure diagnosis for hybrid strategy
        for case in cases:
            ret_items = self.run_strategy("hybrid", case.query, top_k=20)
            ret_ids = [i.chunk_id for i in ret_items]
            lex_ids = [i.chunk_id for i in self.run_strategy("lexical", case.query, top_k=10)]
            sem_ids = [i.chunk_id for i in self.run_strategy("semantic", case.query, top_k=10)]

            diag = self.diagnose_failure(case, ret_ids, lex_ids, sem_ids)
            if diag:
                failure_taxonomy[diag] += 1

        return {
            "total_cases": len(cases),
            "strategies_evaluated": strategies,
            "metrics_by_strategy": strategy_metrics,
            "failure_taxonomy": dict(failure_taxonomy),
            "results_by_strategy": {
                k: [r.to_dict() for r in v] for k, v in strategy_results.items()
            },
        }
