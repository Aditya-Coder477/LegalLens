"""
pipeline/retrieval/config.py
============================
Configuration settings for Phase 5: Hybrid RAG + Retrieval.
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


class RetrievalConfig(BaseModel):
    # Candidate limits
    lexical_top_k: int = Field(
        default=int(os.getenv("LEXICAL_TOP_K", "50")),
        description="Number of lexical candidates to retrieve",
    )
    semantic_top_k: int = Field(
        default=int(os.getenv("SEMANTIC_TOP_K", "50")),
        description="Number of semantic candidates to retrieve",
    )
    final_top_k: int = Field(
        default=int(os.getenv("FINAL_TOP_K", "8")),
        description="Number of final evidence chunks in the bundle",
    )

    # Rank fusion
    rrf_k: int = Field(
        default=int(os.getenv("RRF_K", "60")),
        description="Reciprocal Rank Fusion smoothing parameter k",
    )

    # Reranking
    reranker_enabled: bool = Field(
        default=os.getenv("RERANKER_ENABLED", "false").lower() in ("true", "1", "yes"),
        description="Whether to execute post-fusion reranking",
    )
    reranker_top_n: int = Field(
        default=int(os.getenv("RERANKER_TOP_N", "20")),
        description="Number of top candidates passed to the reranker",
    )

    # Context Expansion limits
    max_parent_context: int = Field(
        default=int(os.getenv("MAX_PARENT_CONTEXT", "1")),
        description="Maximum parent units to expand per retrieved chunk",
    )
    max_sibling_context: int = Field(
        default=int(os.getenv("MAX_SIBLING_CONTEXT", "2")),
        description="Maximum sibling clauses/subsections to expand",
    )
    max_cross_reference_hops: int = Field(
        default=int(os.getenv("MAX_CROSS_REFERENCE_HOPS", "1")),
        description="Maximum cross-reference graph traversal hops",
    )
    max_definition_expansions: int = Field(
        default=int(os.getenv("MAX_DEFINITION_EXPANSIONS", "5")),
        description="Maximum legal definitions to attach as supporting context",
    )

    # Confidence & gating thresholds
    low_evidence_threshold: float = Field(
        default=float(os.getenv("LOW_EVIDENCE_THRESHOLD", "0.010")),
        description="Minimum RRF score threshold below which evidence is considered LOW_EVIDENCE",
    )
    no_evidence_threshold: float = Field(
        default=float(os.getenv("NO_EVIDENCE_THRESHOLD", "0.002")),
        description="RRF score threshold below which retrieval status is NO_EVIDENCE",
    )

    # Cache
    query_cache_enabled: bool = Field(
        default=os.getenv("QUERY_CACHE_ENABLED", "true").lower() in ("true", "1", "yes"),
        description="Enable query embedding caching",
    )


@lru_cache(maxsize=1)
def get_retrieval_config() -> RetrievalConfig:
    return RetrievalConfig()
