"""
pipeline/retrieval/semantic_retriever.py
========================================
Semantic vector retrieval engine using dense embeddings, pgvector / cosine similarity,
query caching, and metadata filters.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from pipeline.knowledge_base.db import DatabaseManager, _cosine_similarity
from pipeline.knowledge_base.db_models import EmbeddingTable, KBChunkTable
from pipeline.knowledge_base.providers import EmbeddingProvider, validate_vector

from .models import Candidate, RetrievalFilters


class SemanticRetriever:
    """
    Retrieves candidate chunks using dense semantic vectors and cosine similarity.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        embedding_provider: EmbeddingProvider,
        query_cache_enabled: bool = True,
    ):
        self.db = db_manager
        self.provider = embedding_provider
        self.query_cache_enabled = query_cache_enabled
        self._query_cache: Dict[str, List[float]] = {}

    def get_query_embedding(self, query: str) -> List[float]:
        """
        Embed the user query with optional in-memory caching.
        """
        q_clean = query.strip()
        cache_key = f"{self.provider.provider_name}:{self.provider.model_name}:{self.provider.dimension}:{q_clean}"

        if self.query_cache_enabled and cache_key in self._query_cache:
            return self._query_cache[cache_key]

        vec = self.provider.embed_text(q_clean)
        validate_vector(vec, self.provider.dimension)

        if self.query_cache_enabled:
            # Simple LRU-style limit
            if len(self._query_cache) > 1000:
                self._query_cache.clear()
            self._query_cache[cache_key] = vec

        return vec

    def retrieve(
        self,
        query: str,
        top_k: int = 50,
        filters: Optional[RetrievalFilters] = None,
        session: Optional[Session] = None,
    ) -> List[Candidate]:
        """
        Execute vector similarity search for the query and return ranked candidates.
        """
        if not query or not query.strip() or top_k <= 0:
            return []

        query_vec = self.get_query_embedding(query)

        def _do_retrieve(s: Session) -> List[Candidate]:
            # Query chunks joined with embeddings
            q_builder = s.query(EmbeddingTable, KBChunkTable).join(
                KBChunkTable, EmbeddingTable.kb_chunk_id == KBChunkTable.kb_chunk_id
            )

            # Apply metadata filters
            if filters:
                if filters.document_id:
                    q_builder = q_builder.filter(KBChunkTable.document_id == filters.document_id)
                if filters.version_id:
                    q_builder = q_builder.filter(KBChunkTable.version_id == filters.version_id)
                if filters.version_group_id:
                    q_builder = q_builder.filter(KBChunkTable.version_group_id == filters.version_group_id)
                if filters.document_type:
                    q_builder = q_builder.filter(KBChunkTable.chunk_type.ilike(f"%{filters.document_type}%"))
                if filters.chunk_type:
                    q_builder = q_builder.filter(KBChunkTable.chunk_type == filters.chunk_type)
                if filters.source_authority:
                    q_builder = q_builder.filter(KBChunkTable.source_authority == filters.source_authority)
                if filters.synthetic is not None:
                    q_builder = q_builder.filter(KBChunkTable.synthetic == filters.synthetic)

            rows = q_builder.all()
            if not rows:
                return []

            scored: List[Tuple[float, KBChunkTable]] = []
            for emb_row, chunk_row in rows:
                if emb_row.dimension != self.provider.dimension:
                    # Reject mismatched vector dimensions (Section 10)
                    continue

                vec = json.loads(emb_row.vector)
                sim = _cosine_similarity(query_vec, vec)
                scored.append((sim, chunk_row))

            # Deterministic sorting
            scored.sort(key=lambda x: (x[0], x[1].document_id, x[1].chunk_id), reverse=True)
            top_matches = scored[:top_k]

            candidates: List[Candidate] = []
            for rank, (score, c) in enumerate(top_matches, 1):
                candidates.append(Candidate(
                    chunk_id=c.chunk_id,
                    kb_chunk_id=c.kb_chunk_id,
                    document_id=c.document_id,
                    version_id=c.version_id,
                    version_group_id=c.version_group_id,
                    score=float(score),
                    method="semantic",
                    semantic_rank=rank,
                    raw_semantic_score=float(score),
                    chunk_data={
                        "title": c.title,
                        "chapter": c.chapter,
                        "section": c.section,
                        "subsection": c.subsection,
                        "clause": c.clause,
                        "parent_unit_id": c.parent_unit_id,
                        "text": c.text,
                        "embedding_text": c.embedding_text,
                        "chunk_type": c.chunk_type,
                        "token_count": c.token_count,
                        "page_start": c.page_start,
                        "page_end": c.page_end,
                        "provenance_id": c.provenance_id,
                        "source_document_id": c.source_document_id,
                        "source_sha256": c.source_sha256,
                        "source_authority": c.source_authority,
                        "synthetic": c.synthetic,
                    }
                ))

            return candidates

        if session:
            return _do_retrieve(session)
        with self.db.session_scope() as s:
            return _do_retrieve(s)
