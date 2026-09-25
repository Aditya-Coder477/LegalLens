"""
pipeline/retrieval/__init__.py
==============================
Phase 5: Hybrid RAG + Retrieval.

Transforms user legal questions into structured evidence bundles using
complementary Lexical (BM25/FTS) and Semantic (pgvector / dense embeddings)
retrieval, Reciprocal Rank Fusion, provenance packaging, and legal context expansion.
"""

from __future__ import annotations

RETRIEVAL_VERSION = "1.0.0"
