"""
pipeline/knowledge_base/db.py
=============================
Database session management, schema initialization, pgvector extension checks,
and vector similarity operations.
"""

from __future__ import annotations

import json
import math
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config import get_kb_config
from .db_models import (
    Base,
    EmbeddingTable,
    IngestionRunTable,
    KBCrossRefTable,
    KBDefinitionTable,
    KBChunkTable,
)
from .models import EmbeddingRecord, KnowledgeBaseChunk


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


class DatabaseManager:
    """
    Manages database connections, table creation, extension validation,
    and vector similarity operations.
    """

    def __init__(self, db_url: Optional[str] = None):
        cfg = get_kb_config()
        self.db_url = db_url or cfg.database_url
        
        # Ensure parent directory exists for SQLite
        if self.db_url.startswith("sqlite:///"):
            sqlite_path = Path(self.db_url.replace("sqlite:///", ""))
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(self.db_url, echo=False)
        self.SessionFactory = sessionmaker(bind=self.engine)
        self.is_postgres = self.db_url.startswith("postgresql")

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def check_connectivity(self) -> Dict[str, Any]:
        """
        Check database connection and return diagnostic info.
        """
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT 1")).scalar()
                dialect_name = self.engine.dialect.name
                return {
                    "connected": res == 1,
                    "dialect": dialect_name,
                    "url": self._mask_url(self.db_url),
                    "error": None,
                }
        except Exception as e:
            return {
                "connected": False,
                "dialect": self.engine.dialect.name,
                "url": self._mask_url(self.db_url),
                "error": str(e),
            }

    def check_pgvector(self) -> Dict[str, Any]:
        """
        Check if pgvector extension is available or installed in PostgreSQL.
        """
        if not self.is_postgres:
            return {
                "available": False,
                "installed": False,
                "note": f"Not a PostgreSQL database ({self.engine.dialect.name}). Fallback cosine similarity active.",
            }

        try:
            with self.engine.connect() as conn:
                # Check if installed
                installed_res = conn.execute(
                    text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                ).scalar()

                # Check if available in system
                avail_res = conn.execute(
                    text("SELECT EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'vector')")
                ).scalar()

                return {
                    "available": bool(avail_res),
                    "installed": bool(installed_res),
                    "note": "pgvector extension check completed.",
                }
        except Exception as e:
            return {
                "available": False,
                "installed": False,
                "error": str(e),
                "note": "Could not check pgvector extension on database.",
            }

    def init_db(self) -> Dict[str, Any]:
        """
        Initialize database schema, verify extension, and create tables/indexes.
        """
        diag = self.check_connectivity()
        if not diag["connected"]:
            return {
                "status": "failed",
                "message": f"Database connection failed: {diag['error']}",
                "diagnostics": diag,
            }

        pgvector_status = {"available": False, "installed": False}
        if self.is_postgres:
            pgvector_status = self.check_pgvector()
            if pgvector_status.get("available") and not pgvector_status.get("installed"):
                try:
                    with self.engine.connect() as conn:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                        conn.commit()
                    pgvector_status["installed"] = True
                except Exception as e:
                    pgvector_status["install_error"] = str(e)

        # Create all tables defined in Base
        Base.metadata.create_all(self.engine)

        # Verify tables created
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        return {
            "status": "success",
            "dialect": self.engine.dialect.name,
            "pgvector": pgvector_status,
            "tables_created": tables,
            "url": self._mask_url(self.db_url),
        }

    def upsert_chunk(self, chunk: KnowledgeBaseChunk, session: Session) -> None:
        """
        Insert or update a knowledge base chunk record.
        """
        existing = session.query(KBChunkTable).filter_by(kb_chunk_id=chunk.kb_chunk_id).first()
        if not existing:
            existing = session.query(KBChunkTable).filter_by(chunk_id=chunk.chunk_id).first()

        domains_str = json.dumps(chunk.legal_domains, ensure_ascii=False)
        if existing:
            existing.document_id = chunk.document_id
            existing.version_group_id = chunk.version_group_id
            existing.version_id = chunk.version_id
            existing.chunk_type = chunk.chunk_type
            existing.title = chunk.title
            existing.chapter = chunk.chapter
            existing.section = chunk.section
            existing.subsection = chunk.subsection
            existing.clause = chunk.clause
            existing.parent_unit_id = chunk.parent_unit_id
            existing.text = chunk.text
            existing.embedding_text = chunk.embedding_text
            existing.page_start = chunk.page_start
            existing.page_end = chunk.page_end
            existing.token_count = chunk.token_count
            existing.legal_domains = domains_str
            existing.synthetic = chunk.synthetic
            existing.source_authority = chunk.source_authority
            existing.source_document_id = chunk.source_document_id
            existing.source_sha256 = chunk.source_sha256
            existing.provenance_id = chunk.provenance_id
            existing.content_hash = chunk.content_hash
            existing.updated_at = chunk.updated_at
        else:
            new_row = KBChunkTable(
                kb_chunk_id=chunk.kb_chunk_id,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                version_group_id=chunk.version_group_id,
                version_id=chunk.version_id,
                chunk_type=chunk.chunk_type,
                title=chunk.title,
                chapter=chunk.chapter,
                section=chunk.section,
                subsection=chunk.subsection,
                clause=chunk.clause,
                parent_unit_id=chunk.parent_unit_id,
                text=chunk.text,
                embedding_text=chunk.embedding_text,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                token_count=chunk.token_count,
                legal_domains=domains_str,
                synthetic=chunk.synthetic,
                source_authority=chunk.source_authority,
                source_document_id=chunk.source_document_id,
                source_sha256=chunk.source_sha256,
                provenance_id=chunk.provenance_id,
                content_hash=chunk.content_hash,
                created_at=chunk.created_at,
                updated_at=chunk.updated_at,
            )
            session.add(new_row)

    def upsert_embedding(self, emb: EmbeddingRecord, session: Session) -> None:
        """
        Store vector embedding.
        """
        existing = session.query(EmbeddingTable).filter_by(
            kb_chunk_id=emb.kb_chunk_id,
            provider=emb.provider,
            model=emb.model,
            dimension=emb.dimension,
        ).first()

        vec_str = json.dumps(emb.vector)
        if existing:
            existing.kb_chunk_id = emb.kb_chunk_id
            existing.vector = vec_str
            existing.embedding_hash = emb.embedding_hash
        else:
            new_row = EmbeddingTable(
                kb_chunk_id=emb.kb_chunk_id,
                content_hash=emb.content_hash,
                provider=emb.provider,
                model=emb.model,
                dimension=emb.dimension,
                vector=vec_str,
                embedding_hash=emb.embedding_hash,
                created_at=emb.created_at,
            )
            session.add(new_row)

    def get_embedding_by_hash(
        self,
        content_hash: str,
        provider: str,
        model: str,
        dimension: int,
        session: Session,
    ) -> Optional[List[float]]:
        """
        Retrieve an existing vector embedding by content_hash + provider + model + dimension.
        """
        row = session.query(EmbeddingTable).filter_by(
            content_hash=content_hash,
            provider=provider,
            model=model,
            dimension=dimension,
        ).first()
        if row and row.vector:
            return json.loads(row.vector)
        return None

    def search_similar_chunks(
        self,
        query_vector: List[float],
        top_k: int = 5,
        session: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity smoke search.
        Returns top_k nearest chunks with metadata and cosine similarity score.
        """
        def _execute(s: Session) -> List[Dict[str, Any]]:
            # Load embeddings and join with chunks
            rows = s.query(EmbeddingTable, KBChunkTable).join(
                KBChunkTable, EmbeddingTable.kb_chunk_id == KBChunkTable.kb_chunk_id
            ).all()

            results = []
            for emb_row, chunk_row in rows:
                vec = json.loads(emb_row.vector)
                score = _cosine_similarity(query_vector, vec)
                results.append({
                    "chunk_id": chunk_row.chunk_id,
                    "kb_chunk_id": chunk_row.kb_chunk_id,
                    "document_id": chunk_row.document_id,
                    "version_id": chunk_row.version_id,
                    "title": chunk_row.title,
                    "section": chunk_row.section,
                    "similarity": round(float(score), 4),
                    "text_preview": (chunk_row.text[:180] + "...") if len(chunk_row.text) > 180 else chunk_row.text,
                    "source_authority": chunk_row.source_authority,
                    "synthetic": chunk_row.synthetic,
                })

            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]

        if session:
            return _execute(session)
        with self.session_scope() as s:
            return _execute(s)

    def _mask_url(self, url: str) -> str:
        if "@" in url:
            prefix, rest = url.split("@", 1)
            scheme = prefix.split("://")[0]
            return f"{scheme}://***:***@{rest}"
        return url
