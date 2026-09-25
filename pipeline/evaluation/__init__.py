"""
pipeline/evaluation
===================
Evaluation, Benchmarking, Security & Quality Gate package for LegalLens Phase 8.
"""

from .citation_evaluator import CitationEvaluator
from .config import EvaluationConfig, get_evaluation_config
from .grounding_evaluator import GroundingEvaluator
from .metrics import (
    compute_citation_metrics,
    compute_grounding_metrics,
    compute_latency_stats,
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from .models import (
    EvaluationCase,
    EvaluationCategory,
    EvaluationLayer,
    EvaluationResult,
    EvaluationStatus,
    QualityGateDimension,
    QualityGateResult,
    QualityGateStatus,
    SecurityFinding,
    SecuritySeverity,
)
from .performance_evaluator import PerformanceEvaluator
from .qa_evaluator import QAEvaluator
from .quality_gate import QualityGate
from .reporter import EvaluationReporter
from .retrieval_evaluator import RetrievalEvaluator
from .safety_evaluator import SafetyEvaluator

__all__ = [
    "EvaluationConfig",
    "get_evaluation_config",
    "EvaluationCase",
    "EvaluationCategory",
    "EvaluationLayer",
    "EvaluationResult",
    "EvaluationStatus",
    "QualityGateDimension",
    "QualityGateResult",
    "QualityGateStatus",
    "SecurityFinding",
    "SecuritySeverity",
    "RetrievalEvaluator",
    "QAEvaluator",
    "GroundingEvaluator",
    "CitationEvaluator",
    "SafetyEvaluator",
    "PerformanceEvaluator",
    "QualityGate",
    "EvaluationReporter",
    "recall_at_k",
    "precision_at_k",
    "hit_rate_at_k",
    "reciprocal_rank",
    "ndcg_at_k",
    "compute_grounding_metrics",
    "compute_citation_metrics",
    "compute_latency_stats",
]
