"""
pipeline/knowledge_base/__init__.py
====================================
Phase 4: Knowledge Base + Embeddings.

Transforms structured legal chunks produced by Phase 3 into a persistent,
searchable, provenance-aware Knowledge Base with vector embeddings.

Modules:
  - config       : Phase 4 configuration settings (DB, provider, dimensions, batching)
  - models       : Canonical Pydantic schemas (KnowledgeBaseChunk, manifests, reports)
  - hashing      : Deterministic content & embedding hashing (SHA-256)
  - providers    : Embedding provider abstraction (Fake, Local, OpenAI)
  - db_models    : SQLAlchemy ORM models with pgvector / relational support
  - db           : Database connection, migration, extension checking, vector search
  - cache        : Embedding reuse & incremental ingestion cache
  - validator    : Input and Knowledge Base validation rules
  - engine       : KnowledgeBaseEngine orchestrating ingestion & statistics
"""

from __future__ import annotations

KB_VERSION = "1.0.0"
DEFAULT_EMBEDDING_DIMENSION = 384
DEFAULT_BATCH_SIZE = 64
DEFAULT_MAX_RETRIES = 3
