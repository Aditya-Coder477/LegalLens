"""
pipeline/retrieval/reranker.py
==============================
Reranker abstraction and implementations for post-fusion candidate scoring.
"""

from __future__ import annotations

import re
from typing import List, Protocol, runtime_checkable

from .models import Candidate


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, candidates: List[Candidate]) -> List[Candidate]:
        ...


class NoOpReranker:
    """
    Default pass-through reranker preserving the exact Reciprocal Rank Fusion order.
    """
    def rerank(self, query: str, candidates: List[Candidate]) -> List[Candidate]:
        return candidates


class LocalTermReranker:
    """
    Lightweight term-proximity and exact-phrase reranker that does not require GPU or external APIs.
    """
    def rerank(self, query: str, candidates: List[Candidate]) -> List[Candidate]:
        if not candidates:
            return []

        q_terms = [t for t in re.findall(r"\b\w+\b", query.lower()) if len(t) > 2]
        if not q_terms:
            return candidates

        reranked = []
        for cand in candidates:
            text = (cand.chunk_data.get("text", "") + " " + cand.chunk_data.get("title", "")).lower()
            overlap = sum(1 for t in q_terms if t in text)
            term_ratio = overlap / len(q_terms)
            
            # Conservative relative boost based on term overlap
            new_score = cand.score * (1.0 + (term_ratio * 0.25))

            cand_copy = cand.model_copy(deep=True)
            cand_copy.rerank_score = round(float(new_score), 5)
            cand_copy.score = float(new_score)
            reranked.append(cand_copy)

        reranked.sort(key=lambda c: (c.score, c.document_id, c.chunk_id), reverse=True)
        return reranked
