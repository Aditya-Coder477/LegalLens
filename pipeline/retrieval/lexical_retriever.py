"""
pipeline/retrieval/lexical_retriever.py
======================================
Lexical retrieval engine supporting SQLite FTS5 (BM25), PostgreSQL FTS,
and fallback term frequency scoring for exact legal provision & phrase matching.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import text
from sqlalchemy.orm import Session

from pipeline.knowledge_base.db import DatabaseManager
from pipeline.knowledge_base.db_models import KBChunkTable

from .models import Candidate, RetrievalFilters
from .query_processor import QueryProcessor


def _tokenize(text: str) -> List[str]:
    """Extract lowercased alphanumeric tokens and legal symbols."""
    return re.findall(r"\b[a-zA-Z0-9_\-\(\)]+\b", text.lower())


class LexicalRetriever:
    """
    Retrieves candidate chunks using exact legal term matching, BM25 / FTS,
    and metadata filters.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.query_processor = QueryProcessor()
        self._fts_initialized = False

    def init_fts(self) -> None:
        """
        Initialize Full-Text Search virtual table if using SQLite.
        """
        if self._fts_initialized:
            return

        if not self.db.is_postgres:
            try:
                with self.db.session_scope() as session:
                    # Check if FTS table exists
                    res = session.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' AND name='kb_chunks_fts'")
                    ).scalar()

                    if not res:
                        session.execute(text("""
                            CREATE VIRTUAL TABLE kb_chunks_fts USING fts5(
                                kb_chunk_id UNINDEXED,
                                chunk_id UNINDEXED,
                                document_id UNINDEXED,
                                section UNINDEXED,
                                title,
                                chapter,
                                text,
                                embedding_text
                            )
                        """))
                        # Populate FTS from knowledge_base_chunks
                        session.execute(text("""
                            INSERT INTO kb_chunks_fts(kb_chunk_id, chunk_id, document_id, section, title, chapter, text, embedding_text)
                            SELECT kb_chunk_id, chunk_id, document_id, section, title, chapter, text, embedding_text
                            FROM knowledge_base_chunks
                        """))
                self._fts_initialized = True
            except Exception:
                # Fallback to in-database column filtering if FTS cannot be created
                pass

    def retrieve(
        self,
        query: str,
        top_k: int = 50,
        filters: Optional[RetrievalFilters] = None,
        session: Optional[Session] = None,
    ) -> List[Candidate]:
        """
        Execute lexical search for the query and return ranked candidates.
        """
        if not query or not query.strip() or top_k <= 0:
            return []

        normalized_q = self.query_processor.normalize(query)
        extracted = self.query_processor.extract_legal_entities(query)

        def _do_retrieve(s: Session) -> List[Candidate]:
            # Apply base query on chunks
            q_builder = s.query(KBChunkTable)

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

            all_chunks = q_builder.all()
            if not all_chunks:
                return []

            # Scoring candidates
            query_tokens = _tokenize(normalized_q)
            query_token_counts = Counter(query_tokens)
            doc_freq: Counter = Counter()

            # Pre-filter candidate matches to avoid heavy computation
            scored_candidates: List[Tuple[float, KBChunkTable]] = []

            # Target exact terms
            target_sections = set(extracted["sections"])
            target_enactments = set(extracted["enactments"])
            target_quoted = [q.lower() for q in extracted["quoted_terms"]]

            for c in all_chunks:
                score = 0.0
                text_lower = c.text.lower()
                emb_lower = (c.embedding_text or "").lower()
                title_lower = (c.title or "").lower()

                # 1. Exact section number match (highest priority for statutory queries)
                if c.section and target_sections:
                    if c.section in target_sections:
                        score += 15.0
                    else:
                        # Match with subsection, e.g. section "10" matches "10(1)"
                        sec_num = c.section.split("(")[0].strip()
                        for ts in target_sections:
                            ts_num = ts.split("(")[0].strip()
                            if sec_num == ts_num:
                                score += 8.0

                # 2. Exact enactment reference match
                if target_enactments:
                    if c.document_id in target_enactments or (c.source_document_id and c.source_document_id in target_enactments):
                        score += 10.0

                # 3. Exact quoted terms
                for qterm in target_quoted:
                    if qterm in text_lower or qterm in emb_lower:
                        score += 6.0

                # 4. Token overlap & frequency scoring
                chunk_tokens = _tokenize(f"{c.title or ''} {c.section or ''} {c.text}")
                chunk_token_set = set(chunk_tokens)
                overlap = sum(query_token_counts[tok] for tok in chunk_tokens if tok in query_token_counts)

                if overlap > 0:
                    # BM25-style term saturation: (tf / (tf + 1.2))
                    tf_score = sum(
                        (cnt / (cnt + 1.2)) for tok, cnt in Counter(chunk_tokens).items() if tok in query_token_counts
                    )
                    score += tf_score * 2.0

                # 5. Title & Chapter keyword boost
                for tok in query_tokens:
                    if tok in title_lower:
                        score += 1.5

                if score > 0.1:
                    scored_candidates.append((score, c))

            scored_candidates.sort(key=lambda x: (x[0], x[1].document_id, x[1].chunk_id), reverse=True)
            top_matches = scored_candidates[:top_k]

            candidates: List[Candidate] = []
            for rank, (score, c) in enumerate(top_matches, 1):
                candidates.append(Candidate(
                    chunk_id=c.chunk_id,
                    kb_chunk_id=c.kb_chunk_id,
                    document_id=c.document_id,
                    version_id=c.version_id,
                    version_group_id=c.version_group_id,
                    score=float(score),
                    method="lexical",
                    lexical_rank=rank,
                    raw_lexical_score=float(score),
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
