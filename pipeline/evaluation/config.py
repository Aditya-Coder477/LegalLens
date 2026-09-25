"""
pipeline/evaluation/config.py
=============================
Configuration settings and quality-gate thresholds for Phase 8 Evaluation & Security.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env", override=False)


class EvaluationConfig(BaseModel):
    # Execution mode and reproducibility
    evaluation_mode: str = Field(
        default=os.getenv("EVALUATION_MODE", "mock"),
        description="Evaluation execution mode: mock | live",
    )
    random_seed: int = Field(
        default=int(os.getenv("EVALUATION_SEED", "20260925")),
        description="Deterministic seed for evaluation reproducibility",
    )

    # Directories
    dataset_dir: Path = Field(
        default=_PROJECT_ROOT / "legal-data" / "evaluation",
        description="Root directory for structured evaluation datasets",
    )
    results_dir: Path = Field(
        default=_PROJECT_ROOT / "evaluation-results",
        description="Directory for reports, manifests, and metrics",
    )

    # Quality Gate Thresholds
    min_recall_at_5: float = Field(
        default=float(os.getenv("MIN_RECALL_AT_5", "0.75")),
        description="Minimum acceptable Recall@5",
    )
    min_recall_at_10: float = Field(
        default=float(os.getenv("MIN_RECALL_AT_10", "0.80")),
        description="Minimum acceptable Recall@10",
    )
    min_mrr: float = Field(
        default=float(os.getenv("MIN_MRR", "0.60")),
        description="Minimum Mean Reciprocal Rank",
    )
    min_ndcg_at_10: float = Field(
        default=float(os.getenv("MIN_NDCG_AT_10", "0.70")),
        description="Minimum Normalized Discounted Cumulative Gain @ 10",
    )

    max_unsupported_claim_rate: float = Field(
        default=float(os.getenv("MAX_UNSUPPORTED_CLAIM_RATE", "0.05")),
        description="Maximum permissible ungrounded claim rate (0.05 = 5%)",
    )
    min_claim_support_rate: float = Field(
        default=float(os.getenv("MIN_CLAIM_SUPPORT_RATE", "0.85")),
        description="Minimum acceptable grounded claim support rate",
    )
    max_contradiction_rate: float = Field(
        default=float(os.getenv("MAX_CONTRADICTION_RATE", "0.00")),
        description="Maximum permissible direct contradiction rate (0% tolerance)",
    )

    min_citation_validity_rate: float = Field(
        default=float(os.getenv("MIN_CITATION_VALIDITY_RATE", "0.95")),
        description="Minimum percentage of citations that must resolve in the KB",
    )
    min_citation_coverage: float = Field(
        default=float(os.getenv("MIN_CITATION_COVERAGE", "0.90")),
        description="Minimum percentage of responses with full citation coverage",
    )

    max_critical_security_findings: int = Field(
        default=int(os.getenv("MAX_CRITICAL_SECURITY_FINDINGS", "0")),
        description="Maximum permissible CRITICAL security findings for PASS",
    )
    max_high_security_findings: int = Field(
        default=int(os.getenv("MAX_HIGH_SECURITY_FINDINGS", "0")),
        description="Maximum permissible HIGH security findings for PASS",
    )
    max_regression_failures: int = Field(
        default=int(os.getenv("MAX_REGRESSION_FAILURES", "0")),
        description="Maximum allowable regression test failures",
    )
    max_p95_latency_ms: float = Field(
        default=float(os.getenv("MAX_P95_LATENCY_MS", "4000.0")),
        description="Maximum allowable P95 response latency in milliseconds",
    )
    max_end_to_end_latency_ms: float = Field(
        default=float(os.getenv("MAX_END_TO_END_LATENCY_MS", "4000.0")),
        description="Maximum allowable end-to-end response latency in milliseconds",
    )
    max_retrieval_latency_ms: float = Field(
        default=float(os.getenv("MAX_RETRIEVAL_LATENCY_MS", "500.0")),
        description="Maximum allowable retrieval latency in milliseconds",
    )
    max_citation_verification_latency_ms: float = Field(
        default=float(os.getenv("MAX_CITATION_VERIFICATION_LATENCY_MS", "200.0")),
        description="Maximum allowable citation verification latency in milliseconds",
    )


@lru_cache(maxsize=1)
def get_evaluation_config() -> EvaluationConfig:
    return EvaluationConfig()
