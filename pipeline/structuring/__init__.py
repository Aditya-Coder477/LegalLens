"""
pipeline/structuring/__init__.py
=================================
Phase 3: Legal Document Structuring & Provenance-Preserving Chunking.

Transforms validated synthetic legal corpus into structured, legally meaningful,
provenance-preserving retrieval corpus.

Pipeline:
    RAW DOCUMENT → LEGAL UNITS → CHUNKS (with embedding_text + retrieval_text)

Components:
    models      - LegalUnit, ChunkRecord, DefinitionRecord, CrossReferenceRecord
    parser      - Multi-type legal structure parser (Act/Rule/Judgment/Contract/etc.)
    chunker     - Legal-aware hierarchical chunker
    extractor   - Definition & cross-reference extractor
    engine      - Orchestration engine
"""

from __future__ import annotations

STRUCTURING_VERSION = "1.0.0"
MAX_TOKENS_DEFAULT = 900
TARGET_TOKENS_DEFAULT = 600
MIN_TOKENS_DEFAULT = 100
OVERLAP_TOKENS_DEFAULT = 50
