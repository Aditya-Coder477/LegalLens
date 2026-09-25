"""
pipeline/knowledge_base/models.py
==================================
Canonical Pydantic models for Phase 4: Knowledge Base + Embeddings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class KnowledgeBaseChunk(BaseModel):
    """
    Canonical Knowledge Base Record representing an embedded, provenance-aware legal chunk.
    """
    kb_chunk_id: str = Field(default_factory=lambda: f"kb-{uuid4()}")
    chunk_id: str
    document_id: str
    version_group_id: Optional[str] = None
    version_id: Optional[str] = None

    chunk_type: str = "SECTION"
    title: Optional[str] = None

    chapter: Optional[str] = None
    section: Optional[str] = None
    subsection: Optional[str] = None
    clause: Optional[str] = None
    parent_unit_id: Optional[str] = None

    text: str
    embedding_text: str

    page_start: Optional[int] = None
    page_end: Optional[int] = None

    token_count: int = 0
    legal_domains: List[str] = Field(default_factory=list)

    synthetic: bool = True
    source_authority: str = "SYNTHETIC"

    source_document_id: Optional[str] = None
    source_sha256: Optional[str] = None
    provenance_id: Optional[str] = None

    embedding_provider: str = "local"
    embedding_model: str = "legal-dense-v1"
    embedding_dimension: int = 384

    embedding_created_at: Optional[str] = None

    content_hash: str
    embedding_hash: Optional[str] = None

    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class EmbeddingRecord(BaseModel):
    """
    Vector embedding record corresponding to a KnowledgeBaseChunk.
    """
    kb_chunk_id: str
    chunk_id: str
    content_hash: str
    provider: str
    model: str
    dimension: int
    vector: List[float]
    embedding_hash: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class EmbeddingManifest(BaseModel):
    """
    Manifest created at legal-data/knowledge_base/manifests/embedding_manifest.json (Section 22).
    """
    run_id: str = Field(default_factory=lambda: f"run-{uuid4().hex[:8]}")
    started_at: str
    completed_at: str

    input_file: str
    input_sha256: str

    total_chunks: int = 0
    new_embeddings: int = 0
    reused_embeddings: int = 0
    failed_embeddings: int = 0
    skipped_embeddings: int = 0

    provider: str
    model: str
    dimension: int

    embedding_version: str = "1.0.0"

    synthetic_chunk_count: int = 0
    non_synthetic_chunk_count: int = 0

    database_target: str
    status: str = "completed"


class KnowledgeBaseManifest(BaseModel):
    """
    Manifest created at legal-data/knowledge_base/manifests/knowledge_base_manifest.json (Section 23).
    """
    kb_version: str = "1.0.0"
    created_at: str
    updated_at: str

    source_corpus: str = "synthetic"
    source_corpus_sha256: str

    total_documents: int = 0
    total_versions: int = 0
    total_legal_units: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0

    embedding_provider: str
    embedding_model: str
    embedding_dimension: int

    synthetic_documents: int = 0
    official_documents: int = 0
    user_documents: int = 0

    schema_version: str = "1.0.0"


class KBQualityReport(BaseModel):
    """
    Report created at legal-data/knowledge_base/reports/kb_quality_report.json (Section 34).
    """
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    documents: int = 0
    versions: int = 0
    legal_units: int = 0
    chunks: int = 0

    embedded_chunks: int = 0
    missing_embeddings: int = 0
    failed_embeddings: int = 0

    synthetic_chunks: int = 0
    official_chunks: int = 0
    user_chunks: int = 0

    chunk_types: Dict[str, int] = Field(default_factory=dict)
    legal_domains: Dict[str, int] = Field(default_factory=dict)

    average_tokens: float = 0.0
    min_tokens: int = 0
    max_tokens: int = 0

    embedding_dimension: int = 384
    embedding_model: str = "legal-dense-v1"

    duplicate_content_hashes: int = 0
    orphan_records: int = 0
    missing_provenance: int = 0

    database_status: str = "healthy"
    embedding_coverage: float = 1.0


class EmbeddingStats(BaseModel):
    """
    Stats created at legal-data/knowledge_base/embeddings/embedding_stats.json (Section 35).
    """
    total_chunks: int = 0
    embedded: int = 0
    failed: int = 0
    reused: int = 0
    new: int = 0
    dimension: int = 384
    provider: str = "local"
    model: str = "legal-dense-v1"
