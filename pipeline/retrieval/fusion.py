"""
pipeline/retrieval/fusion.py
============================
Hybrid Rank Fusion implementing Reciprocal Rank Fusion (RRF).
Combines disparate uncalibrated lexical and semantic ranking lists transparently.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .models import Candidate


class FusionEngine:
    """
    Combines lexical and semantic candidate lists using Reciprocal Rank Fusion.
    """

    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k

    def fuse(
        self,
        lexical_candidates: List[Candidate],
        semantic_candidates: List[Candidate],
        top_k: int = 20,
    ) -> List[Candidate]:
        """
        Merge lexical and semantic candidate lists using RRF formula:
            score(c) = sum(1.0 / (k + rank))
        """
        # Map by unique chunk key: (document_id, version_id, chunk_id)
        fused_map: Dict[str, Dict[str, Any]] = {}

        # 1. Process Lexical Candidates
        for rank, cand in enumerate(lexical_candidates, 1):
            key = cand.kb_chunk_id or f"{cand.document_id}:{cand.version_id}:{cand.chunk_id}"
            rrf_val = 1.0 / (self.rrf_k + rank)

            fused_map[key] = {
                "candidate": cand,
                "rrf_score": rrf_val,
                "lexical_rank": rank,
                "semantic_rank": None,
                "raw_lexical_score": cand.raw_lexical_score,
                "raw_semantic_score": None,
                "methods": {"lexical"},
            }

        # 2. Process Semantic Candidates
        for rank, cand in enumerate(semantic_candidates, 1):
            key = cand.kb_chunk_id or f"{cand.document_id}:{cand.version_id}:{cand.chunk_id}"
            rrf_val = 1.0 / (self.rrf_k + rank)

            if key in fused_map:
                fused_map[key]["rrf_score"] += rrf_val
                fused_map[key]["semantic_rank"] = rank
                fused_map[key]["raw_semantic_score"] = cand.raw_semantic_score
                fused_map[key]["methods"].add("semantic")
                # Ensure chunk data is filled if lexical had less data
                if not fused_map[key]["candidate"].chunk_data and cand.chunk_data:
                    fused_map[key]["candidate"].chunk_data = cand.chunk_data
            else:
                fused_map[key] = {
                    "candidate": cand,
                    "rrf_score": rrf_val,
                    "lexical_rank": None,
                    "semantic_rank": rank,
                    "raw_lexical_score": None,
                    "raw_semantic_score": cand.raw_semantic_score,
                    "methods": {"semantic"},
                }

        # Build fused candidate objects
        fused_list: List[Candidate] = []
        for key, entry in fused_map.items():
            base_cand = entry["candidate"]
            methods_sorted = sorted(list(entry["methods"]))
            method_str = "+".join(methods_sorted)

            fused_cand = Candidate(
                chunk_id=base_cand.chunk_id,
                kb_chunk_id=base_cand.kb_chunk_id,
                document_id=base_cand.document_id,
                version_id=base_cand.version_id,
                version_group_id=base_cand.version_group_id,
                score=float(entry["rrf_score"]),
                method=method_str,
                lexical_rank=entry["lexical_rank"],
                semantic_rank=entry["semantic_rank"],
                raw_lexical_score=entry["raw_lexical_score"],
                raw_semantic_score=entry["raw_semantic_score"],
                chunk_data=base_cand.chunk_data,
            )
            fused_list.append(fused_cand)

        # Deterministic sorting (Section 54): RRF score descending, then doc_id, version_id, chunk_id
        fused_list.sort(
            key=lambda c: (
                c.score,
                c.document_id,
                c.version_id or "",
                c.chunk_id,
            ),
            reverse=True,
        )

        return fused_list[:top_k]
