"""
tests/evaluation/test_metrics.py
================================
Unit tests for Phase 8 evaluation metrics:
- Recall@K
- Precision@K
- HitRate@K
- Reciprocal Rank (MRR)
- NDCG@K with graded relevance
- Grounding metrics
- Citation metrics
- Latency percentiles
"""

import pytest

from pipeline.evaluation.metrics import (
    compute_citation_metrics,
    compute_grounding_metrics,
    compute_latency_stats,
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k():
    retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
    targets = {"doc2", "doc5", "doc9"}

    # At K=1, doc1 is not relevant
    assert recall_at_k(retrieved, targets, k=1) == 0.0

    # At K=2, doc2 is relevant (1 of 3 targets)
    assert round(recall_at_k(retrieved, targets, k=2), 2) == 0.33

    # At K=5, doc2 and doc5 are relevant (2 of 3 targets)
    assert round(recall_at_k(retrieved, targets, k=5), 2) == 0.67

    # Empty targets should return 1.0
    assert recall_at_k(retrieved, set(), k=5) == 1.0


def test_precision_at_k():
    retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
    targets = {"doc2", "doc3"}

    # At K=2, doc1 (no), doc2 (yes) -> 1/2 = 0.5
    assert precision_at_k(retrieved, targets, k=2) == 0.5

    # At K=3, doc2 and doc3 are yes -> 2/3 = 0.667
    assert round(precision_at_k(retrieved, targets, k=3), 2) == 0.67


def test_hit_rate_at_k():
    retrieved = ["doc1", "doc2", "doc3"]
    targets = {"doc2"}

    assert hit_rate_at_k(retrieved, targets, k=1) == 0.0
    assert hit_rate_at_k(retrieved, targets, k=2) == 1.0
    assert hit_rate_at_k(retrieved, targets, k=3) == 1.0


def test_reciprocal_rank():
    # Target at rank 1
    assert reciprocal_rank(["doc1", "doc2"], {"doc1"}) == 1.0

    # Target at rank 2
    assert reciprocal_rank(["doc1", "doc2"], {"doc2"}) == 0.5

    # Target at rank 4
    assert reciprocal_rank(["doc1", "doc2", "doc3", "doc4"], {"doc4"}) == 0.25

    # Target not found
    assert reciprocal_rank(["doc1", "doc2"], {"docX"}) == 0.0


def test_ndcg_at_k():
    # Ideal ranking: 3, 2, 1, 0 -> NDCG = 1.0
    perfect_rel = [3, 2, 1, 0]
    assert ndcg_at_k(perfect_rel, k=4) == 1.0

    # Suboptimal ranking
    suboptimal = [0, 1, 2, 3]
    ndcg = ndcg_at_k(suboptimal, k=4)
    assert 0.0 < ndcg < 1.0

    # All zeros
    assert ndcg_at_k([0, 0, 0], k=3) == 0.0


def test_grounding_metrics():
    statuses = ["ENTAILED", "ENTAILED", "PARTIALLY_ENTAILED", "UNGROUNDED"]
    res = compute_grounding_metrics(statuses)

    assert res["total_claims"] == 4
    assert res["claim_support_rate"] == 0.5
    assert res["partial_support_rate"] == 0.25
    assert res["unsupported_claim_rate"] == 0.25
    assert res["contradiction_rate"] == 0.0


def test_citation_metrics():
    res = compute_citation_metrics(
        total_citations=10,
        valid_citations=9,
        sha256_matches=9,
        expected_citations=10,
        retrieved_citations=10,
    )

    assert res["citation_validity_rate"] == 0.9
    assert res["sha256_match_rate"] == 0.9


def test_latency_stats():
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    stats = compute_latency_stats(latencies)

    assert stats["count"] == 10
    assert stats["min"] == 10.0
    assert stats["max"] == 100.0
    assert stats["median"] == 55.0
    assert stats["p95"] >= 90.0
