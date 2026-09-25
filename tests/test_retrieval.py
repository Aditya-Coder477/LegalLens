"""
tests/test_retrieval.py
=======================
Comprehensive test suite for Phase 5: Hybrid RAG + Retrieval.

Tests cover:
  - Query processing (normalization, legal entity extraction, intent detection)
  - Lexical retrieval (exact section match, enactment match, token overlap, filtering)
  - Semantic retrieval (vector similarity, dimension validation, filtering)
  - Hybrid fusion (Reciprocal Rank Fusion, method tracking, deterministic sorting)
  - Candidate deduplication (version & document isolation)
  - Context expansion (parent sections, definitions, cross-references)
  - Reranking (NoOp, LocalTermReranker)
  - Evidence gating & NO_EVIDENCE safety (no fabricated evidence)
  - Provenance preservation in final EvidenceBundle
  - End-to-end integration test
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

import pytest

from pipeline.knowledge_base.db import DatabaseManager
from pipeline.knowledge_base.db_models import (
    EmbeddingTable,
    KBCrossRefTable,
    KBDefinitionTable,
    KBChunkTable,
)
from pipeline.knowledge_base.hashing import compute_content_hash
from pipeline.knowledge_base.models import EmbeddingRecord, KnowledgeBaseChunk
from pipeline.knowledge_base.providers import FakeEmbeddingProvider
from pipeline.retrieval.config import RetrievalConfig
from pipeline.retrieval.context_expander import ContextExpander
from pipeline.retrieval.deduplication import CandidateDeduplicator
from pipeline.retrieval.evidence import EvidenceBuilder
from pipeline.retrieval.fusion import FusionEngine
from pipeline.retrieval.lexical_retriever import LexicalRetriever
from pipeline.retrieval.models import (
    Candidate,
    EvidenceBundle,
    QueryType,
    RetrievalFilters,
    RetrievalStatus,
    SupportingContext,
)
from pipeline.retrieval.query_processor import QueryProcessor
from pipeline.retrieval.reranker import LocalTermReranker, NoOpReranker
from pipeline.retrieval.retriever import HybridRetriever
from pipeline.retrieval.semantic_retriever import SemanticRetriever


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def fake_provider():
    return FakeEmbeddingProvider(model_name="test-dense", dimension=32, normalize=True)


@pytest.fixture
def temp_db(tmp_path, fake_provider):
    db_file = tmp_path / "test_retrieval.db"
    db = DatabaseManager(f"sqlite:///{db_file}")
    db.init_db()

    # Populate 3 test chunks
    with db.session_scope() as s:
        # Chunk 1: Act Section 10 (Obligations)
        c1 = KBChunkTable(
            kb_chunk_id="kb-c1",
            chunk_id="SYN-ACT-001-CH-III-S10",
            document_id="SYN-ACT-001",
            version_id="v1.0-original",
            version_group_id="vg-001",
            chunk_type="SECTION",
            title="Reporting and Compliance Obligations",
            chapter="Chapter III: Obligations",
            section="10",
            text="Every regulated organization shall file a quarterly compliance return detailing all actions taken.",
            embedding_text="Reporting and Compliance Obligations Section 10",
            token_count=15,
            page_start=5,
            page_end=5,
            synthetic=True,
            source_authority="SYNTHETIC",
            source_document_id="SYN-ACT-001",
            source_sha256="1" * 64,
            provenance_id="prov-c1",
            content_hash="hash-c1",
        )
        s.add(c1)
        v1 = fake_provider.embed_text(c1.embedding_text)
        s.add(EmbeddingTable(
            kb_chunk_id="kb-c1",
            content_hash="hash-c1",
            provider=fake_provider.provider_name,
            model=fake_provider.model_name,
            dimension=fake_provider.dimension,
            vector=json.dumps(v1),
            embedding_hash="emb-c1",
        ))

        # Chunk 2: Child subsection (Obligations)
        c2 = KBChunkTable(
            kb_chunk_id="kb-c2",
            chunk_id="SYN-ACT-001-CH-III-S10-SS1",
            document_id="SYN-ACT-001",
            version_id="v1.0-original",
            version_group_id="vg-001",
            chunk_type="SUBSECTION",
            title="Quarterly Return Filing",
            chapter="Chapter III: Obligations",
            section="10(1)",
            parent_unit_id="SYN-ACT-001-CH-III-S10",
            text="The compliance return shall be submitted electronically by the fifteenth day.",
            embedding_text="Quarterly Return Filing Section 10(1)",
            token_count=12,
            page_start=5,
            page_end=5,
            synthetic=True,
            source_authority="SYNTHETIC",
            source_document_id="SYN-ACT-001",
            source_sha256="1" * 64,
            provenance_id="prov-c2",
            content_hash="hash-c2",
        )
        s.add(c2)
        v2 = fake_provider.embed_text(c2.embedding_text)
        s.add(EmbeddingTable(
            kb_chunk_id="kb-c2",
            content_hash="hash-c2",
            provider=fake_provider.provider_name,
            model=fake_provider.model_name,
            dimension=fake_provider.dimension,
            vector=json.dumps(v2),
            embedding_hash="emb-c2",
        ))

        # Chunk 3: Contract Clause (Termination)
        c3 = KBChunkTable(
            kb_chunk_id="kb-c3",
            chunk_id="SYN-CONT-001-CLAUSE-3",
            document_id="SYN-CONT-001",
            version_id="v1.0",
            version_group_id="vg-cont-001",
            chunk_type="CONTRACT_CLAUSE",
            title="Termination for Convenience",
            chapter=None,
            section="3",
            text="Either party may terminate this Master Services Agreement without cause by providing 30 days prior written notice.",
            embedding_text="Termination for Convenience Clause 3",
            token_count=20,
            page_start=1,
            page_end=2,
            synthetic=True,
            source_authority="SYNTHETIC",
            source_document_id="SYN-CONT-001",
            source_sha256="2" * 64,
            provenance_id="prov-c3",
            content_hash="hash-c3",
        )
        s.add(c3)
        v3 = fake_provider.embed_text(c3.embedding_text)
        s.add(EmbeddingTable(
            kb_chunk_id="kb-c3",
            content_hash="hash-c3",
            provider=fake_provider.provider_name,
            model=fake_provider.model_name,
            dimension=fake_provider.dimension,
            vector=json.dumps(v3),
            embedding_hash="emb-c3",
        ))

        # Add definition and cross-reference
        s.add(KBDefinitionTable(
            definition_id="def-1",
            document_id="SYN-ACT-001",
            term="regulated organization",
            definition_text="Any entity designated as an intermediary under Section 3.",
            source_section_id="SYN-ACT-001-SEC-2",
            synthetic=True,
            source_authority="SYNTHETIC",
        ))
        s.add(KBCrossRefTable(
            reference_id="ref-1",
            source_unit_id="SYN-ACT-001-UNIT-SEC10",
            source_document_id="SYN-ACT-001",
            target_reference="Section 3",
            reference_type="SECTION_REFERENCE",
            resolved_target_document_id="SYN-ACT-001",
            synthetic=True,
            source_authority="SYNTHETIC",
        ))

    return db


# ──────────────────────────────────────────────
# 1. Query Processor Tests
# ──────────────────────────────────────────────

def test_query_normalization():
    qp = QueryProcessor()
    raw = "  What   are   the obligations under Section  10?  \n"
    norm = qp.normalize(raw)
    assert norm == "What are the obligations under Section 10?"


def test_legal_entity_extraction():
    qp = QueryProcessor()
    q = 'What are the rules under Section 12(2)(a) and Rule 8 of SYN-ACT-001 regarding "data fiduciary"?'
    extracted = qp.extract_legal_entities(q)
    assert "12(2)(a)" in extracted["sections"]
    assert "8" in extracted["rules"]
    assert "SYN-ACT-001" in extracted["enactments"]
    assert "data fiduciary" in extracted["quoted_terms"]


def test_query_type_detection():
    qp = QueryProcessor()
    assert qp.detect_query_type("What does Section 12 say?") == QueryType.SECTION_LOOKUP
    assert qp.detect_query_type("Define 'appropriate government'") == QueryType.DEFINITION
    assert qp.detect_query_type("What are the mandatory statutory compliance obligations?") == QueryType.OBLIGATION
    assert qp.detect_query_type("What is the penalty for failure to file returns?") == QueryType.PENALTY
    assert qp.detect_query_type("What is the right to deletion?") == QueryType.RIGHT
    assert qp.detect_query_type("What happens on termination of contract?") == QueryType.CONTRACT_CLAUSE
    assert qp.detect_query_type("What was held by the court in the judgment?") == QueryType.JUDGMENT
    assert qp.detect_query_type("What provision does Section 10 refer to?") == QueryType.CROSS_REFERENCE
    assert qp.detect_query_type("How to file an appeal and what is the timeline?") == QueryType.PROCEDURE


# ──────────────────────────────────────────────
# 2. Lexical Retrieval Tests
# ──────────────────────────────────────────────

def test_lexical_retrieval_exact_section(temp_db):
    lex = LexicalRetriever(temp_db)
    results = lex.retrieve(query="What does Section 10 state?", top_k=5)
    assert len(results) > 0
    top = results[0]
    assert "S10" in top.chunk_id
    assert top.method == "lexical"
    assert top.score > 10.0  # Boosted for exact section match


def test_lexical_retrieval_with_filter(temp_db):
    lex = LexicalRetriever(temp_db)
    # Filter by contract doc type
    filt = RetrievalFilters(chunk_type="CONTRACT_CLAUSE")
    results = lex.retrieve(query="terminate agreement", top_k=5, filters=filt)
    assert len(results) == 1
    assert results[0].chunk_id == "SYN-CONT-001-CLAUSE-3"


# ──────────────────────────────────────────────
# 3. Semantic Retrieval Tests
# ──────────────────────────────────────────────

def test_semantic_retrieval(temp_db, fake_provider):
    sem = SemanticRetriever(temp_db, fake_provider)
    results = sem.retrieve(query="Reporting and compliance returns", top_k=2)
    assert len(results) > 0
    assert results[0].method == "semantic"
    assert -1.0 <= results[0].score <= 1.0


def test_semantic_retrieval_empty_query(temp_db, fake_provider):
    sem = SemanticRetriever(temp_db, fake_provider)
    assert sem.retrieve(query="") == []


# ──────────────────────────────────────────────
# 4. Hybrid Rank Fusion (RRF) Tests
# ──────────────────────────────────────────────

def test_rrf_fusion():
    fusion = FusionEngine(rrf_k=60)
    c1 = Candidate(chunk_id="chunk-1", kb_chunk_id="kb-1", document_id="doc1", score=10.0, method="lexical")
    c2 = Candidate(chunk_id="chunk-2", kb_chunk_id="kb-2", document_id="doc2", score=5.0, method="lexical")
    c3 = Candidate(chunk_id="chunk-1", kb_chunk_id="kb-1", document_id="doc1", score=0.8, method="semantic")
    c4 = Candidate(chunk_id="chunk-3", kb_chunk_id="kb-3", document_id="doc3", score=0.7, method="semantic")

    fused = fusion.fuse(lexical_candidates=[c1, c2], semantic_candidates=[c3, c4], top_k=5)
    assert len(fused) == 3
    # chunk-1 appears in both lexical rank 1 and semantic rank 1 -> highest score
    assert fused[0].chunk_id == "chunk-1"
    assert "lexical+semantic" in fused[0].method
    # RRF score = 1/(60+1) + 1/(60+1) = 2/61 ≈ 0.03278
    expected = (1.0 / 61) + (1.0 / 61)
    assert pytest.approx(fused[0].score, rel=1e-3) == expected


def test_deduplicator():
    dedup = CandidateDeduplicator()
    c1 = Candidate(chunk_id="c1", kb_chunk_id="kb1", document_id="d1", version_id="v1", score=0.5)
    c2 = Candidate(chunk_id="c1", kb_chunk_id="kb1", document_id="d1", version_id="v1", score=0.3)
    c3 = Candidate(chunk_id="c1", kb_chunk_id="kb1", document_id="d1", version_id="v2", score=0.4)  # Different version!

    deduped = dedup.deduplicate([c1, c2, c3])
    # c1-v1 duplicate removed, but c1-v2 preserved!
    assert len(deduped) == 2
    assert deduped[0].version_id == "v1"
    assert deduped[1].version_id == "v2"


# ──────────────────────────────────────────────
# 5. Context Expansion Tests
# ──────────────────────────────────────────────

def test_context_expansion(temp_db):
    expander = ContextExpander(temp_db, max_parents=1, max_definitions=2, max_cross_refs=1)
    # Candidate c2 is a subsection with parent SYN-ACT-001-CH-III-S10
    cand = Candidate(
        chunk_id="SYN-ACT-001-CH-III-S10-SS1",
        kb_chunk_id="kb-c2",
        document_id="SYN-ACT-001",
        chunk_data={
            "parent_unit_id": "SYN-ACT-001-CH-III-S10",
            "text": "Every regulated organization must file return as per Section 3.",
        }
    )
    ctx = expander.expand([cand])
    # Parent expansion
    assert len(ctx.parent_chunks) == 1
    assert ctx.parent_chunks[0]["chunk_id"] == "SYN-ACT-001-CH-III-S10"

    # Definition expansion ('regulated organization')
    assert len(ctx.definitions) == 1
    assert ctx.definitions[0]["term"] == "regulated organization"

    # Cross-reference expansion ('Section 3')
    assert len(ctx.cross_references) == 1
    assert ctx.cross_references[0]["target_reference"] == "Section 3"


# ──────────────────────────────────────────────
# 6. Reranker Tests
# ──────────────────────────────────────────────

def test_noop_reranker():
    r = NoOpReranker()
    cands = [Candidate(chunk_id="c1", kb_chunk_id="kb1", document_id="d1", score=0.8)]
    assert r.rerank("test", cands) == cands


def test_local_term_reranker():
    r = LocalTermReranker()
    c1 = Candidate(
        chunk_id="c1", kb_chunk_id="kb1", document_id="d1", score=0.1,
        chunk_data={"title": "Data Privacy", "text": "Something else"}
    )
    c2 = Candidate(
        chunk_id="c2", kb_chunk_id="kb2", document_id="d2", score=0.1,
        chunk_data={"title": "Data Retention Obligations", "text": "Mandatory data retention requirements"}
    )
    reranked = r.rerank("data retention", [c1, c2])
    # c2 has more overlapping query terms and should receive a higher score
    assert reranked[0].chunk_id == "c2"


# ──────────────────────────────────────────────
# 7. Evidence Gating & No-Evidence Tests
# ──────────────────────────────────────────────

def test_no_evidence_gating():
    cfg = RetrievalConfig(no_evidence_threshold=0.05)
    eb = EvidenceBuilder(cfg)
    cand = Candidate(chunk_id="c1", kb_chunk_id="kb1", document_id="d1", score=0.001)  # Weak score
    bundle = eb.build_bundle(
        query="Irrelevant nonsensical query",
        normalized_query="irrelevant nonsensical query",
        query_type=QueryType.GENERAL,
        candidates=[cand],
        supporting_context=SupportingContext(),
    )
    assert bundle.retrieval_status == RetrievalStatus.NO_EVIDENCE
    assert len(bundle.results) == 0  # Evidence is not fabricated


# ──────────────────────────────────────────────
# 8. Provenance Preservation & End-to-End Tests
# ──────────────────────────────────────────────

def test_provenance_preservation(temp_db, fake_provider):
    cfg = RetrievalConfig(final_top_k=2, no_evidence_threshold=0.0001, low_evidence_threshold=0.001)
    retriever = HybridRetriever(
        db_manager=temp_db,
        embedding_provider=fake_provider,
        config=cfg,
    )
    bundle = retriever.retrieve("Section 10 compliance return")
    assert len(bundle.results) > 0
    top = bundle.results[0]

    # Verify all provenance fields are intact
    assert top.source_document_id == "SYN-ACT-001"
    assert top.source_sha256 == "1" * 64
    assert top.provenance_id in ("prov-c1", "prov-c2")
    assert top.synthetic is True
    assert top.source_authority == "SYNTHETIC"
    assert top.page_start == 5
    assert top.page_end == 5
    assert len(top.retrieval_methods) > 0


def test_end_to_end_hybrid_retrieval(temp_db, fake_provider):
    retriever = HybridRetriever(
        db_manager=temp_db,
        embedding_provider=fake_provider,
    )
    bundle = retriever.retrieve(
        query="What are the compliance return obligations under Section 10?",
        top_k=3,
        debug=True,
    )

    assert bundle.query_type == QueryType.OBLIGATION
    assert bundle.retrieval_status in (RetrievalStatus.FOUND, RetrievalStatus.LOW_EVIDENCE)
    assert bundle.debug_info is not None
    assert "latencies_ms" in bundle.debug_info
    assert len(bundle.results) >= 1
    assert "SYN-ACT-001" in [r.document_id for r in bundle.results]
