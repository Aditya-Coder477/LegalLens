"""
pipeline/retrieval/deduplication.py
===================================
Deduplication of candidate retrieval streams preserving legal version isolation.
"""

from __future__ import annotations

from typing import Dict, List, Set

from .models import Candidate


class CandidateDeduplicator:
    """
    Deduplicates candidates across stages while maintaining version and document integrity.
    """

    def deduplicate(self, candidates: List[Candidate]) -> List[Candidate]:
        """
        Deduplicate candidates by (document_id, version_id, chunk_id).
        Preserves the first (highest scoring) occurrence.
        """
        seen: Set[str] = set()
        deduped: List[Candidate] = []

        for cand in candidates:
            key = f"{cand.document_id}::{cand.version_id or ''}::{cand.chunk_id}"
            if key not in seen:
                seen.add(key)
                deduped.append(cand)

        return deduped
