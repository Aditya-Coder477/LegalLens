"""
pipeline/knowledge_base/db_models.py
====================================
SQLAlchemy database models for Knowledge Base and vector storage.
Supports both PostgreSQL (+ pgvector when available) and SQLite for local development.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class KBChunkTable(Base):
    """
    Relational table for canonical knowledge base legal chunks.
    """
    __tablename__ = "knowledge_base_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_chunk_id = Column(String(128), unique=True, nullable=False, index=True)
    chunk_id = Column(String(128), nullable=False, index=True)
    document_id = Column(String(64), nullable=False, index=True)
    version_group_id = Column(String(64), nullable=True, index=True)
    version_id = Column(String(64), nullable=True, index=True)
    chunk_type = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=True)

    chapter = Column(String(128), nullable=True)
    section = Column(String(64), nullable=True)
    subsection = Column(String(64), nullable=True)
    clause = Column(String(64), nullable=True)
    parent_unit_id = Column(String(128), nullable=True)

    text = Column(Text, nullable=False)
    embedding_text = Column(Text, nullable=False)

    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)

    token_count = Column(Integer, default=0)
    legal_domains = Column(Text, default="[]")  # JSON encoded list

    synthetic = Column(Boolean, default=True, nullable=False, index=True)
    source_authority = Column(String(64), default="SYNTHETIC", nullable=False, index=True)

    source_document_id = Column(String(64), nullable=True)
    source_sha256 = Column(String(64), nullable=True)
    provenance_id = Column(String(128), nullable=True)

    content_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(String(64), default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String(64), default=lambda: datetime.utcnow().isoformat())

    __table_args__ = (
        Index("idx_doc_version", "document_id", "version_id"),
        Index("idx_chunk_content_hash", "chunk_id", "content_hash"),
    )


class EmbeddingTable(Base):
    """
    Relational / Vector storage table for chunk embeddings.
    """
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_chunk_id = Column(String(128), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, index=True)
    provider = Column(String(64), nullable=False)
    model = Column(String(128), nullable=False)
    dimension = Column(Integer, nullable=False)
    vector = Column(Text, nullable=False)  # JSON-serialized list of floats
    embedding_hash = Column(String(64), nullable=False)
    created_at = Column(String(64), default=lambda: datetime.utcnow().isoformat())

    __table_args__ = (
        Index("idx_embed_lookup", "content_hash", "provider", "model", "dimension"),
    )


class KBDefinitionTable(Base):
    """
    Relational table for extracted legal definitions linked to documents.
    """
    __tablename__ = "kb_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    definition_id = Column(String(128), unique=True, nullable=False)
    document_id = Column(String(64), nullable=False, index=True)
    term = Column(String(256), nullable=False, index=True)
    definition_text = Column(Text, nullable=False)
    source_section_id = Column(String(128), nullable=True)
    synthetic = Column(Boolean, default=True)
    source_authority = Column(String(64), default="SYNTHETIC")


class KBCrossRefTable(Base):
    """
    Relational table for extracted cross-references.
    """
    __tablename__ = "kb_cross_references"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_id = Column(String(128), unique=True, nullable=False)
    source_unit_id = Column(String(128), nullable=False, index=True)
    source_document_id = Column(String(64), nullable=False, index=True)
    target_reference = Column(String(256), nullable=False)
    reference_type = Column(String(64), nullable=False)
    resolved_target_document_id = Column(String(64), nullable=True, index=True)
    synthetic = Column(Boolean, default=True)
    source_authority = Column(String(64), default="SYNTHETIC")


class IngestionRunTable(Base):
    """
    Audit table for tracking knowledge base ingestion runs.
    """
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, nullable=False)
    started_at = Column(String(64), nullable=False)
    completed_at = Column(String(64), nullable=True)
    total_chunks = Column(Integer, default=0)
    new_embeddings = Column(Integer, default=0)
    reused_embeddings = Column(Integer, default=0)
    failed_embeddings = Column(Integer, default=0)
    status = Column(String(32), default="started")
