"""
pipeline/retrieval/evidence.py
==============================
Packages ranked candidates into provenance-preserving RetrievedEvidence records
and builds the final canonical EvidenceBundle for Phase 6.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import RetrievalConfig, get_retrieval_config
from .models import (
    Candidate,
    EvidenceBundle,
    QueryType,
    RetrievalFilters,
    RetrievalStatus,
    RetrievedEvidence,
    SupportingContext,
)


class EvidenceBuilder:
    """
    Transforms candidates into ranked, provenance-rich evidence items
    and applies evidence confidence gating.
    """

    def __init__(self, config: Optional[RetrievalConfig] = None):
        self.config = config or get_retrieval_config()

    def build_bundle(
        self,
        query: str,
        normalized_query: str,
        query_type: QueryType,
        candidates: List[Candidate],
        supporting_context: SupportingContext,
        filters: Optional[RetrievalFilters] = None,
        debug_info: Optional[Dict[str, Any]] = None,
    ) -> EvidenceBundle:
        """
        Assemble the final EvidenceBundle.
        """
        # Determine retrieval status based on candidate count and top score
        if not candidates:
            status = RetrievalStatus.NO_EVIDENCE
            results: List[RetrievedEvidence] = []
        else:
            top_score = candidates[0].score
            if top_score < self.config.no_evidence_threshold:
                status = RetrievalStatus.NO_EVIDENCE
                results = []  # Do not return weakly-related noise as evidence (Section 35)
            elif top_score < self.config.low_evidence_threshold:
                status = RetrievalStatus.LOW_EVIDENCE
                results = self._package_evidence(candidates[: self.config.final_top_k])
            else:
                status = RetrievalStatus.FOUND
                results = self._package_evidence(candidates[: self.config.final_top_k])

        return EvidenceBundle(
            query=query,
            normalized_query=normalized_query,
            query_type=query_type,
            retrieval_status=status,
            filters=filters,
            retrieval_config=self.config.model_dump(),
            results=results,
            supporting_context=supporting_context,
            retrieval_timestamp=datetime.utcnow().isoformat(),
            debug_info=debug_info,
        )

    def _package_evidence(self, candidates: List[Candidate]) -> List[RetrievedEvidence]:
        """
        Convert Candidate models to RetrievedEvidence preserving all provenance fields.
        """
        evidence_list: List[RetrievedEvidence] = []

        for rank, cand in enumerate(candidates, 1):
            c_data = cand.chunk_data or {}
            methods = cand.method.split("+") if cand.method else ["hybrid"]

            item = RetrievedEvidence(
                rank=rank,
                chunk_id=cand.chunk_id,
                kb_chunk_id=cand.kb_chunk_id,
                document_id=cand.document_id,
                version_group_id=cand.version_group_id,
                version_id=cand.version_id,
                document_title=c_data.get("document_title"),
                document_type=c_data.get("document_type"),
                chunk_type=c_data.get("chunk_type", "SECTION"),
                title=c_data.get("title"),
                chapter=c_data.get("chapter"),
                section=c_data.get("section"),
                subsection=c_data.get("subsection"),
                clause=c_data.get("clause"),
                text=c_data.get("text", ""),
                lexical_score=cand.raw_lexical_score,
                semantic_score=cand.raw_semantic_score,
                fusion_score=round(cand.score, 5),
                rerank_score=cand.rerank_score,
                source_authority=c_data.get("source_authority", "SYNTHETIC"),
                synthetic=bool(c_data.get("synthetic", True)),
                page_start=c_data.get("page_start"),
                page_end=c_data.get("page_end"),
                provenance_id=c_data.get("provenance_id"),
                source_document_id=c_data.get("source_document_id"),
                source_sha256=c_data.get("source_sha256"),
                retrieval_methods=methods,
            )
            evidence_list.append(item)

        return evidence_list
