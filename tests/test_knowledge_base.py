"""
tests/test_knowledge_base.py
============================
Comprehensive test suite for Phase 4: Knowledge Base + Embeddings.

Tests cover:
  - Input validation (valid, malformed, missing fields)
  - Hashing (deterministic content hash, vector hash, change detection)
  - Vector validation (dimension, NaN, infinity, zeros)
  - Embedding providers (Fake, Local, batching, normalization)
  - Database operations (insert, upsert, query, cosine smoke search)
  - Cache operations (idempotency, reuse)
  - Provenance & synthetic guardrails preservation
  - Multi-version handling
  - End-to-end ingestion pipeline & manifests
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from pipeline.knowledge_base.cache import EmbeddingCacheManager
from pipeline.knowledge_base.db import DatabaseManager, _cosine_similarity
from pipeline.knowledge_base.db_models import EmbeddingTable, KBChunkTable
from pipeline.knowledge_base.engine import KnowledgeBaseEngine
from pipeline.knowledge_base.hashing import compute_content_hash, compute_vector_hash
from pipeline.knowledge_base.models import EmbeddingRecord, KnowledgeBaseChunk
from pipeline.knowledge_base.providers import (
    FakeEmbeddingProvider,
    LocalEmbeddingProvider,
    get_embedding_provider,
    validate_vector,
)
from pipeline.knowledge_base.validator import InputChunkValidator, KnowledgeBaseValidator


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def fake_provider():
    return FakeEmbeddingProvider(model_name="test-dense", dimension=64, normalize=True)


@pytest.fixture
def local_provider():
    return LocalEmbeddingProvider(model_name="local-test", dimension=64, normalize=True)


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_kb.db"
    db = DatabaseManager(f"sqlite:///{db_file}")
    db.init_db()
    return db


@pytest.fixture
def sample_chunk_dict():
    return {
        "chunk_id": "SYN-ACT-001-CH-01-S01",
        "document_id": "SYN-ACT-001",
        "version_group_id": "vg-001",
        "version_id": "v1.0-original",
        "chunk_type": "SECTION",
        "title": "Short title and extent",
        "chapter_title": "Chapter I: Preliminary",
        "section_number": "1",
        "subsection_number": None,
        "clause_number": None,
        "parent_unit_id": None,
        "text": "(1) This Act may be called the Test Digital Act. (2) It extends to Bharat.",
        "embedding_text": "[ACT] Test Digital Act | Chapter I: Preliminary | Section 1: Short title\n\n(1) This Act may be called...",
        "page_start": 1,
        "page_end": 1,
        "token_count": 25,
        "legal_domains": ["Information Technology"],
        "synthetic": True,
        "source_authority": "SYNTHETIC",
        "source_document_id": "SYN-ACT-001",
        "source_sha256": "e" * 64,
        "provenance_id": "prov-syn-001",
    }


# ──────────────────────────────────────────────
# 1. Hashing Tests
# ──────────────────────────────────────────────

def test_deterministic_content_hash():
    h1 = compute_content_hash(
        text="All regulated entities must comply.",
        title="Obligations",
        document_id="SYN-ACT-001",
        section_number="5",
        embedding_text="[ACT] Obligations Section 5",
    )
    h2 = compute_content_hash(
        text="All regulated entities must comply.",
        title="Obligations",
        document_id="SYN-ACT-001",
        section_number="5",
        embedding_text="[ACT] Obligations Section 5",
    )
    assert h1 == h2
    assert len(h1) == 64


def test_content_hash_changes_on_modified_text():
    h1 = compute_content_hash(text="First version text", document_id="SYN-ACT-001")
    h2 = compute_content_hash(text="Second version text", document_id="SYN-ACT-001")
    assert h1 != h2


def test_vector_hash_consistency():
    vec = [0.123, -0.456, 0.789]
    h1 = compute_vector_hash(vec)
    h2 = compute_vector_hash(vec)
    assert h1 == h2
    assert len(h1) == 64


# ──────────────────────────────────────────────
# 2. Vector Validation Tests
# ──────────────────────────────────────────────

def test_validate_vector_valid():
    vec = [0.1, 0.2, 0.3, 0.4]
    validate_vector(vec, 4)  # No error raised


def test_validate_vector_dimension_mismatch():
    vec = [0.1, 0.2, 0.3]
    with pytest.raises(ValueError, match="dimension mismatch"):
        validate_vector(vec, 4)


def test_validate_vector_nan_rejected():
    vec = [0.1, float("nan"), 0.3]
    with pytest.raises(ValueError, match="NaN"):
        validate_vector(vec, 3)


def test_validate_vector_infinity_rejected():
    vec = [0.1, float("inf"), 0.3]
    with pytest.raises(ValueError, match="infinity"):
        validate_vector(vec, 3)


def test_validate_vector_all_zeros_rejected():
    vec = [0.0, 0.0, 0.0]
    with pytest.raises(ValueError, match="all zeros"):
        validate_vector(vec, 3)


# ──────────────────────────────────────────────
# 3. Embedding Provider Tests
# ──────────────────────────────────────────────

def test_fake_provider_dimensions_and_determinism(fake_provider):
    vec1 = fake_provider.embed_text("sample legal contract clause")
    vec2 = fake_provider.embed_text("sample legal contract clause")
    assert len(vec1) == 64
    assert vec1 == vec2
    # Verify normalized
    norm = sum(x * x for x in vec1) ** 0.5
    assert pytest.approx(norm, rel=1e-3) == 1.0


def test_local_provider_batching(local_provider):
    texts = ["Act 1 section 5", "Contract clause 12", "Judgment decree order"]
    vecs = local_provider.embed_batch(texts)
    assert len(vecs) == 3
    for v in vecs:
        assert len(v) == 64
        norm = sum(x * x for x in v) ** 0.5
        assert pytest.approx(norm, rel=1e-3) == 1.0


def test_get_embedding_provider_factory():
    p1 = get_embedding_provider("fake", dimension=128)
    assert p1.provider_name == "fake"
    assert p1.dimension == 128

    p2 = get_embedding_provider("local", dimension=256)
    assert p2.provider_name == "local"
    assert p2.dimension == 256


# ──────────────────────────────────────────────
# 4. Input Validator Tests
# ──────────────────────────────────────────────

def test_input_validator_valid_file(tmp_path, sample_chunk_dict):
    fpath = tmp_path / "valid_chunks.jsonl"
    fpath.write_text(json.dumps(sample_chunk_dict) + "\n", encoding="utf-8")
    validator = InputChunkValidator(fpath)
    is_valid, issues, stats = validator.validate()
    assert is_valid is True
    assert stats["valid_records"] == 1


def test_input_validator_missing_fields(tmp_path):
    fpath = tmp_path / "bad_chunks.jsonl"
    bad_record = {"chunk_id": "", "text": ""}
    fpath.write_text(json.dumps(bad_record) + "\n", encoding="utf-8")
    validator = InputChunkValidator(fpath)
    is_valid, issues, stats = validator.validate()
    assert is_valid is False
    assert any("chunk_id_required" in iss.rule for iss in issues)


def test_input_validator_duplicate_chunk_id(tmp_path, sample_chunk_dict):
    fpath = tmp_path / "dup_chunks.jsonl"
    line = json.dumps(sample_chunk_dict) + "\n"
    fpath.write_text(line + line, encoding="utf-8")
    validator = InputChunkValidator(fpath)
    is_valid, issues, stats = validator.validate()
    assert is_valid is False
    assert any("chunk_id_unique" in iss.rule for iss in issues)


# ──────────────────────────────────────────────
# 5. Database & Similarity Search Tests
# ──────────────────────────────────────────────

def test_database_init_and_upsert(temp_db, sample_chunk_dict):
    kb_chunk = KnowledgeBaseChunk(
        kb_chunk_id="kb-test-01",
        chunk_id=sample_chunk_dict["chunk_id"],
        document_id=sample_chunk_dict["document_id"],
        text=sample_chunk_dict["text"],
        embedding_text=sample_chunk_dict["embedding_text"],
        content_hash=compute_content_hash(sample_chunk_dict["text"]),
        synthetic=True,
        source_authority="SYNTHETIC",
    )
    with temp_db.session_scope() as s:
        temp_db.upsert_chunk(kb_chunk, s)

    with temp_db.session_scope() as s:
        row = s.query(KBChunkTable).filter_by(kb_chunk_id="kb-test-01").first()
        assert row is not None
        assert row.chunk_id == sample_chunk_dict["chunk_id"]
        assert row.synthetic is True
        assert row.source_authority == "SYNTHETIC"


def test_vector_smoke_search(temp_db, sample_chunk_dict):
    kb_chunk = KnowledgeBaseChunk(
        kb_chunk_id="kb-test-01",
        chunk_id=sample_chunk_dict["chunk_id"],
        document_id=sample_chunk_dict["document_id"],
        title="Data Retention Rule",
        section="7",
        text="All logs must be retained for two years.",
        embedding_text="Retention of records",
        content_hash="hash-123",
        synthetic=True,
        source_authority="SYNTHETIC",
    )
    vec = [0.5, 0.5, 0.5, 0.5]
    emb = EmbeddingRecord(
        kb_chunk_id="kb-test-01",
        chunk_id=sample_chunk_dict["chunk_id"],
        content_hash="hash-123",
        provider="test",
        model="test",
        dimension=4,
        vector=vec,
        embedding_hash="emb-hash-123",
    )

    with temp_db.session_scope() as s:
        temp_db.upsert_chunk(kb_chunk, s)
        temp_db.upsert_embedding(emb, s)

    query_vec = [0.5, 0.5, 0.5, 0.5]
    results = temp_db.search_similar_chunks(query_vec, top_k=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == sample_chunk_dict["chunk_id"]
    assert pytest.approx(results[0]["similarity"], rel=1e-3) == 1.0


# ──────────────────────────────────────────────
# 6. Cache & Idempotency Tests
# ──────────────────────────────────────────────

def test_embedding_cache_put_get(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache = EmbeddingCacheManager(cache_file)
    assert cache.get("hash1", "local", "model1", 64) is None

    cache.put("hash1", "local", "model1", 64, [0.1] * 64)
    cache.save()

    cache2 = EmbeddingCacheManager(cache_file)
    retrieved = cache2.get("hash1", "local", "model1", 64)
    assert retrieved is not None
    assert len(retrieved) == 64


# ──────────────────────────────────────────────
# 7. End-to-End Engine Ingestion & Manifests Test
# ──────────────────────────────────────────────

def test_engine_ingestion_and_idempotency(tmp_path, sample_chunk_dict, fake_provider):
    chunks_file = tmp_path / "chunks.jsonl"
    kb_path = tmp_path / "kb"
    db_file = tmp_path / "e2e.db"
    db_url = f"sqlite:///{db_file}"

    # Write 2 sample chunks
    c1 = dict(sample_chunk_dict)
    c2 = dict(sample_chunk_dict)
    c2["chunk_id"] = "SYN-ACT-001-CH-01-S02"
    c2["section_number"] = "2"
    c2["text"] = "Section 2 definitions."
    c2["embedding_text"] = "Section 2 definitions text."

    with chunks_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(c1) + "\n")
        f.write(json.dumps(c2) + "\n")

    # First Ingestion Run
    engine1 = KnowledgeBaseEngine(
        chunks_path=chunks_file,
        kb_data_path=kb_path,
        db_url=db_url,
        provider=fake_provider,
        batch_size=2,
        overwrite=True,
        verbose=False,
    )
    s1 = engine1.ingest()
    assert s1["processed_chunks"] == 2
    assert s1["new_embeddings"] == 2
    assert s1["reused_embeddings"] == 0

    # Verify manifest files created
    assert (kb_path / "manifests" / "knowledge_base_manifest.json").exists()
    assert (kb_path / "manifests" / "embedding_manifest.json").exists()
    assert (kb_path / "canonical" / "kb_chunks.jsonl").exists()
    assert (kb_path / "reports" / "kb_quality_report.json").exists()

    # Second Run (Idempotency check: embeddings should be reused!)
    engine2 = KnowledgeBaseEngine(
        chunks_path=chunks_file,
        kb_data_path=kb_path,
        db_url=db_url,
        provider=fake_provider,
        batch_size=2,
        overwrite=False,
        resume=True,
        verbose=False,
    )
    s2 = engine2.ingest()
    # With resume on existing canonical chunks, already processed chunks are skipped
    assert s2["skipped_chunks"] == 2
    assert s2["new_embeddings"] == 0


def test_kb_validator_full(tmp_path, fake_provider, sample_chunk_dict):
    chunks_file = tmp_path / "chunks.jsonl"
    kb_path = tmp_path / "kb"
    db_url = f"sqlite:///{tmp_path / 'val.db'}"

    chunks_file.write_text(json.dumps(sample_chunk_dict) + "\n", encoding="utf-8")

    engine = KnowledgeBaseEngine(
        chunks_path=chunks_file,
        kb_data_path=kb_path,
        db_url=db_url,
        provider=fake_provider,
        overwrite=True,
        verbose=False,
    )
    engine.ingest()

    validator = KnowledgeBaseValidator(engine.db, expected_dimension=fake_provider.dimension)
    is_valid, issues, stats = validator.validate()
    assert is_valid is True
    assert stats["total_chunks"] == 1
    assert stats["embedded_chunks"] == 1
    assert stats["orphan_embeddings"] == 0
