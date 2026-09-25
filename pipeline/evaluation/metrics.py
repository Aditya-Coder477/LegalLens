"""
pipeline/evaluation/metrics.py
==============================
Mathematical metrics computation engine for LegalLens Phase 8.
Supports:
- Information Retrieval: Recall@K, Precision@K, HitRate@K, MRR, NDCG@K (graded 0..3)
- Grounding & Faithfulness: Claim support, unsupported, and contradiction rates
- Citation: Validity rate, SHA-256 match rate
- Latency & Performance: Mean, Median (P50), P95, P99, Min, Max
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set


# ──────────────────────────────────────────────
# 1. Information Retrieval Metrics
# ──────────────────────────────────────────────

def recall_at_k(retrieved_ids: List[str], target_ids: Set[str], k: int = 10) -> float:
    """
    Calculate Recall@K: proportion of relevant target items retrieved in top-K.
    """
    if not target_ids:
        return 1.0
    retrieved_k = set(retrieved_ids[:k])
    hits = len(retrieved_k.intersection(target_ids))
    return round(hits / len(target_ids), 4)


def precision_at_k(retrieved_ids: List[str], target_ids: Set[str], k: int = 10) -> float:
    """
    Calculate Precision@K: proportion of top-K retrieved items that are relevant targets.
    """
    if k <= 0:
        return 0.0
    retrieved_k = set(retrieved_ids[:k])
    hits = len(retrieved_k.intersection(target_ids))
    return round(hits / k, 4)


def hit_rate_at_k(retrieved_ids: List[str], target_ids: Set[str], k: int = 10) -> float:
    """
    Calculate HitRate@K (1.0 if at least one target is in top-K, 0.0 otherwise).
    """
    retrieved_k = set(retrieved_ids[:k])
    return 1.0 if len(retrieved_k.intersection(target_ids)) > 0 else 0.0


def reciprocal_rank(retrieved_ids: List[str], target_ids: Set[str]) -> float:
    """
    Calculate Reciprocal Rank (1/rank of first relevant item, or 0.0 if not found).
    """
    for rank, item in enumerate(retrieved_ids, 1):
        if item in target_ids:
            return round(1.0 / rank, 4)
    return 0.0


def ndcg_at_k(
    retrieved_or_gains: Any,
    relevance_scores: Optional[Any] = None,
    k: int = 10,
) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain (NDCG@K) with graded relevance (0..3).
    Supports two signatures:
      1. ndcg_at_k(gains_list, k=10)
      2. ndcg_at_k(retrieved_ids, relevance_scores_dict, k=10)
    """
    if isinstance(relevance_scores, int):
        k_val = relevance_scores
        gains = list(retrieved_or_gains)
    elif isinstance(relevance_scores, dict):
        k_val = k
        gains = [relevance_scores.get(item, 0) for item in retrieved_or_gains]
    else:
        k_val = k
        gains = list(retrieved_or_gains)

    if not gains:
        return 1.0

    # 1. Compute DCG@K
    dcg = 0.0
    for rank, rel in enumerate(gains[:k_val], 1):
        dcg += (math.pow(2, rel) - 1.0) / math.log2(rank + 1)

    # 2. Compute Ideal DCG (IDCG@K)
    sorted_ideal = sorted(gains, reverse=True)[:k_val]
    idcg = 0.0
    for rank, rel in enumerate(sorted_ideal, 1):
        idcg += (math.pow(2, rel) - 1.0) / math.log2(rank + 1)

    if idcg <= 0.0:
        return 0.0

    return round(dcg / idcg, 4)


# ──────────────────────────────────────────────
# 2. Grounding & Claim Metrics
# ──────────────────────────────────────────────

def compute_grounding_metrics(claim_verifications: List[Any]) -> Dict[str, float]:
    """
    Calculate claim support rate, unsupported claim rate, contradiction rate,
    and partial support rate from ClaimVerificationResult objects or status strings.
    """
    if not claim_verifications:
        return {
            "claim_support_rate": 1.0,
            "unsupported_claim_rate": 0.0,
            "partial_support_rate": 0.0,
            "contradiction_rate": 0.0,
            "total_claims": 0,
        }

    def _get_status_str(c: Any) -> str:
        if isinstance(c, str):
            return c
        status = getattr(c, "status", None)
        if status is not None:
            return getattr(status, "value", str(status))
        return str(c)

    total = len(claim_verifications)
    statuses = [_get_status_str(c) for c in claim_verifications]

    supported = sum(1 for s in statuses if s == "ENTAILED")
    partial = sum(1 for s in statuses if s == "PARTIALLY_ENTAILED")
    contradicted = sum(1 for s in statuses if s == "CONTRADICTED")
    ungrounded = sum(1 for s in statuses if s in ("UNGROUNDED", "UNSUPPORTED"))

    return {
        "claim_support_rate": round(supported / total, 4),
        "partial_support_rate": round(partial / total, 4),
        "unsupported_claim_rate": round(ungrounded / total, 4),
        "contradiction_rate": round(contradicted / total, 4),
        "total_claims": total,
    }


# ──────────────────────────────────────────────
# 3. Citation Metrics
# ──────────────────────────────────────────────

def compute_citation_metrics(
    citation_verifications: Optional[List[Any]] = None,
    total_citations: Optional[int] = None,
    valid_citations: Optional[int] = None,
    sha256_matches: Optional[int] = None,
    expected_citations: Optional[int] = None,
    retrieved_citations: Optional[int] = None,
) -> Dict[str, float]:
    """
    Calculate citation validity, coverage, and provenance match rate.
    Supports list of results or explicit numerical counts.
    """
    if citation_verifications is not None:
        total = len(citation_verifications)
        if total == 0:
            return {
                "citation_validity_rate": 1.0,
                "sha256_match_rate": 1.0,
                "total_citations": 0,
            }
        valid = sum(
            1 for c in citation_verifications
            if getattr(c, "is_valid", False) or getattr(c, "status", None) in ("VERIFIED", "SUPERSEDED_VERSION")
        )
        with_sha = sum(
            1 for c in citation_verifications
            if getattr(c, "hash_matched", False) or getattr(c, "source_sha256", None)
        )
        return {
            "citation_validity_rate": round(valid / total, 4),
            "sha256_match_rate": round(with_sha / max(1, valid), 4),
            "total_citations": total,
        }

    # Explicit counts signature
    tot = total_citations or 0
    val = valid_citations or 0
    sha = sha256_matches or 0

    val_rate = round(val / tot, 4) if tot > 0 else 1.0
    sha_rate = round(sha / tot, 4) if tot > 0 else 1.0

    return {
        "citation_validity_rate": val_rate,
        "sha256_match_rate": sha_rate,
        "total_citations": tot,
        "valid_citations": val,
    }


# ──────────────────────────────────────────────
# 4. Latency / Performance Percentiles
# ──────────────────────────────────────────────

def compute_latency_stats(latencies_ms: List[float]) -> Dict[str, float]:
    """
    Compute mean, median (P50), P95, P99, min, and max latency percentiles in milliseconds.
    """
    if not latencies_ms:
        return {
            "mean": 0.0,
            "median": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "min": 0.0,
            "max": 0.0,
            "count": 0,
        }

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)

    def percentile(p: float) -> float:
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_lats[int(k)]
        d0 = sorted_lats[int(f)] * (c - k)
        d1 = sorted_lats[int(c)] * (k - f)
        return d0 + d1

    mean_val = sum(sorted_lats) / n
    median_val = percentile(0.50)
    p95_val = percentile(0.95)
    p99_val = percentile(0.99)

    return {
        "mean": round(mean_val, 2),
        "median": round(median_val, 2),
        "p50": round(median_val, 2),
        "p95": round(p95_val, 2),
        "p99": round(p99_val, 2),
        "min": round(sorted_lats[0], 2),
        "max": round(sorted_lats[-1], 2),
        "count": n,
    }
