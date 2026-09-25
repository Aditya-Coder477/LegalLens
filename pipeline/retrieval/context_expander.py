"""
pipeline/retrieval/context_expander.py
======================================
Controlled legal context expansion:
  1. Parent unit & section expansion
  2. Cross-reference graph traversal (max 1 hop)
  3. Term definition lookup from the Knowledge Base
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from pipeline.knowledge_base.db import DatabaseManager
from pipeline.knowledge_base.db_models import (
    KBCrossRefTable,
    KBDefinitionTable,
    KBChunkTable,
)

from .models import Candidate, SupportingContext


class ContextExpander:
    """
    Expands retrieved legal chunks with parent context, relevant statutory definitions,
    and referenced provisions without polluting primary evidence ranking.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        max_parents: int = 1,
        max_cross_refs: int = 1,
        max_definitions: int = 5,
    ):
        self.db = db_manager
        self.max_parents = max_parents
        self.max_cross_refs = max_cross_refs
        self.max_definitions = max_definitions

    def expand(
        self,
        candidates: List[Candidate],
        session: Optional[Session] = None,
    ) -> SupportingContext:
        """
        Extract supporting context for the top retrieved candidates.
        """
        if not candidates:
            return SupportingContext()

        def _do_expand(s: Session) -> SupportingContext:
            parent_chunks: List[Dict[str, Any]] = []
            definitions: List[Dict[str, Any]] = []
            cross_refs: List[Dict[str, Any]] = []

            seen_parents: Set[str] = set()
            seen_defs: Set[str] = set()
            seen_xrefs: Set[str] = set()

            for cand in candidates[:5]:  # Focus expansion on top 5 candidates
                doc_id = cand.document_id
                c_data = cand.chunk_data or {}
                parent_unit_id = c_data.get("parent_unit_id")
                text_content = c_data.get("text", "")

                # 1. Parent context expansion
                if parent_unit_id and len(parent_chunks) < self.max_parents:
                    # Look up parent chunk by unit_id or section
                    parent_row = s.query(KBChunkTable).filter(
                        KBChunkTable.document_id == doc_id,
                        (KBChunkTable.chunk_id == parent_unit_id) | (KBChunkTable.kb_chunk_id == f"kb-{parent_unit_id}"),
                    ).first()

                    if parent_row and parent_row.chunk_id not in seen_parents and parent_row.chunk_id != cand.chunk_id:
                        seen_parents.add(parent_row.chunk_id)
                        parent_chunks.append({
                            "chunk_id": parent_row.chunk_id,
                            "document_id": parent_row.document_id,
                            "section": parent_row.section,
                            "title": parent_row.title,
                            "text": parent_row.text,
                            "relation": "parent_section",
                        })

                # 2. Definition lookup
                if len(definitions) < self.max_definitions:
                    doc_defs = s.query(KBDefinitionTable).filter(
                        KBDefinitionTable.document_id == doc_id
                    ).all()

                    for d in doc_defs:
                        if len(definitions) >= self.max_definitions:
                            break
                        if d.term.lower() in text_content.lower() and d.term.lower() not in seen_defs:
                            seen_defs.add(d.term.lower())
                            definitions.append({
                                "term": d.term,
                                "definition_text": d.definition_text,
                                "document_id": d.document_id,
                                "source_section_id": d.source_section_id,
                            })

                # 3. Cross-reference expansion
                if len(cross_refs) < self.max_cross_refs:
                    # Query existing cross references for this doc / unit
                    refs = s.query(KBCrossRefTable).filter(
                        KBCrossRefTable.source_document_id == doc_id
                    ).limit(5).all()

                    for r in refs:
                        if len(cross_refs) >= self.max_cross_refs:
                            break
                        if r.target_reference in text_content and r.target_reference not in seen_xrefs:
                            seen_xrefs.add(r.target_reference)
                            cross_refs.append({
                                "source_document_id": r.source_document_id,
                                "target_reference": r.target_reference,
                                "reference_type": r.reference_type,
                                "resolved_document_id": r.resolved_target_document_id,
                            })

            return SupportingContext(
                parent_chunks=parent_chunks,
                definitions=definitions,
                cross_references=cross_refs,
            )

        if session:
            return _do_expand(session)
        with self.db.session_scope() as s:
            return _do_expand(s)
