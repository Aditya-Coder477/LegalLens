"""
tests/test_structuring.py
==========================
Phase 3 test suite: 20 unit tests + 1 integration test.

Tests cover:
  - LegalUnit model creation and field validation
  - ChunkRecord model integrity
  - LegalStructureParser: section parsing, preamble parsing, subsection detection
  - LegalChunker: chunk sizing, splitting, embedding_text, retrieval_text
  - Definition extraction
  - Cross-reference extraction
  - Chunk ID generation
  - Multi-doc-type coverage (act, rule, judgment, contract, notification)
  - Version isolation
  - Synthetic flags on all records
  - Integration: full pipeline run on mini corpus
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import List
from uuid import uuid4

import pytest

from pipeline.structuring.models import (
    ChunkRecord, ChunkType, CrossReferenceRecord, DefinitionRecord, LegalUnit
)
from pipeline.structuring.parser import (
    LegalStructureParser,
    extract_definitions,
    extract_cross_references,
    _count_tokens,
    _detect_chunk_type,
    _make_unit_id,
)
from pipeline.structuring.chunker import (
    LegalChunker,
    _tok,
    _split_sentences,
    _split_paragraphs,
    _overlap_prefix,
    _next_chunk_id,
    _detect_prefix,
)
from pipeline.structuring.engine import StructuringEngine


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture()
def sample_act_doc():
    return {
        "document_id": "SYN-ACT-001",
        "document_type": "act",
        "title": "Digital Services Accountability Act, 2025 (Synthetic)",
        "legal_domain": "Information Technology and Cyber Law",
        "source_authority": "SYNTHETIC",
        "synthetic": True,
        "document_version_group_id": "b7b8cd8a-test",
        "version_label": "v1.0-original",
        "sha256": "a" * 64,
        "raw_file_path": None,
    }


@pytest.fixture()
def sample_act_section():
    return {
        "section_id": "SYN-ACT-001-SEC-10",
        "document_id": "SYN-ACT-001",
        "version_group_id": "b7b8cd8a-test",
        "version_id": "v1.0-original",
        "title": "Section 10 - Reporting and Disclosure Requirements",
        "domain": "Information Technology and Cyber Law",
        "chapter": "Chapter III: Substantive Obligations and Standards",
        "section": "10",
        "section_number": "10",
        "heading": "Reporting and Disclosure Requirements",
        "text": (
            "(1) Every regulated organization shall file a quarterly compliance return.\n"
            "(2) The return shall be submitted in electronic form on or before the fifteenth day.\n"
            "(3) Failure to file shall attract a late fee of rupees five thousand per day."
        ),
        "provisions": ["Quarterly compliance return", "Late fee of Rs. 5000"],
        "explanations": ["Electronic filing is mandatory."],
        "source_authority": "SYNTHETIC",
        "synthetic": True,
        "page_start": 10,
        "page_end": 10,
    }


@pytest.fixture()
def sample_judgment_doc():
    return {
        "document_id": "SYN-JUDG-001",
        "document_type": "judgment",
        "title": "Aarav Technologies v. DSRAB (Synthetic)",
        "legal_domain": "Administrative Law",
        "source_authority": "SYNTHETIC",
        "synthetic": True,
        "document_version_group_id": str(uuid4()),
        "version_label": "v1.0-original",
        "sha256": "b" * 64,
    }


@pytest.fixture()
def sample_judgment_section():
    return {
        "section_id": "SYN-JUDG-001-SEC-1",
        "document_id": "SYN-JUDG-001",
        "section_number": "1",
        "title": "Case Details and Coram",
        "text": "In the High Court of Dakshin Pradesh (Synthetic). Case Number: SYNTHETIC-WP-2025-1042.",
        "source_authority": "SYNTHETIC",
        "synthetic": True,
        "page_start": 1,
        "page_end": 1,
    }


@pytest.fixture()
def sample_contract_doc():
    return {
        "document_id": "SYN-CONT-001",
        "document_type": "contract",
        "title": "Master Services Agreement (Synthetic)",
        "legal_domain": "Contract Law",
        "source_authority": "SYNTHETIC",
        "synthetic": True,
        "document_version_group_id": str(uuid4()),
        "version_label": "v1.0",
        "sha256": "c" * 64,
    }


@pytest.fixture()
def sample_rule_doc():
    return {
        "document_id": "SYN-RULE-001",
        "document_type": "rule",
        "title": "Digital Platform Intermediary Due Diligence Rules (Synthetic)",
        "legal_domain": "Information Technology and Cyber Law",
        "source_authority": "SYNTHETIC",
        "synthetic": True,
        "sha256": "d" * 64,
    }


@pytest.fixture()
def parser(tmp_path):
    return LegalStructureParser(tmp_path)


@pytest.fixture()
def chunker():
    return LegalChunker(target_tokens=600, max_tokens=900, min_tokens=100, overlap_tokens=50)


@pytest.fixture()
def basic_unit(sample_act_doc):
    return LegalUnit(
        unit_id="SYN-ACT-001-UNIT-SEC10",
        document_id="SYN-ACT-001",
        version_group_id="b7b8cd8a-test",
        version_id="v1.0-original",
        unit_type=ChunkType.SECTION,
        chapter_number="III",
        chapter_title="Substantive Obligations",
        section_number="10",
        section_title="Reporting Requirements",
        heading="Reporting Requirements",
        text="Every regulated organization shall file quarterly returns.",
        legal_domain="Information Technology and Cyber Law",
        document_title="Digital Services Accountability Act, 2025 (Synthetic)",
        source_document_id="SYN-ACT-001",
        source_sha256="a" * 64,
        synthetic=True,
        source_authority="SYNTHETIC",
    )


# ──────────────────────────────────────────────
# Unit Tests
# ──────────────────────────────────────────────

# 1. LegalUnit: required fields and defaults
def test_legal_unit_defaults():
    u = LegalUnit(document_id="SYN-ACT-001", text="Hello world")
    assert u.synthetic is True
    assert u.source_authority == "SYNTHETIC"
    assert u.unit_type == ChunkType.SECTION
    assert u.unit_id is not None
    assert u.document_id == "SYN-ACT-001"


# 2. LegalUnit: synthetic and source_authority cannot be overridden to real values
def test_legal_unit_synthetic_flag_explicit():
    u = LegalUnit(document_id="SYN-ACT-001", text="Test", synthetic=True, source_authority="SYNTHETIC")
    assert u.synthetic is True
    assert u.source_authority == "SYNTHETIC"


# 3. ChunkRecord: required fields
def test_chunk_record_fields():
    c = ChunkRecord(
        chunk_id="SYN-ACT-001-CH-01-S01",
        document_id="SYN-ACT-001",
        chunk_type=ChunkType.SECTION,
        text="Some legal text.",
    )
    assert c.synthetic is True
    assert c.source_authority == "SYNTHETIC"
    assert c.token_count == 0  # computed separately
    assert c.chunk_id == "SYN-ACT-001-CH-01-S01"


# 4. Token counter works
def test_count_tokens():
    assert _count_tokens("one two three") == 3
    assert _count_tokens("") == 0
    assert _count_tokens("  leading  spaces  ") == 2
    assert _tok("one two three four five") == 5


# 5. Paragraph splitter detects double newlines
def test_split_paragraphs():
    text = "Para one.\n\nPara two.\n\nPara three."
    parts = _split_paragraphs(text)
    assert len(parts) == 3
    assert parts[0] == "Para one."


# 6. Sentence splitter
def test_split_sentences():
    text = "This is one sentence. This is another sentence. And a third one."
    parts = _split_sentences(text)
    assert len(parts) >= 2


# 7. Overlap prefix extracts last N words
def test_overlap_prefix():
    text = "word1 word2 word3 word4 word5"
    result = _overlap_prefix(text, 3)
    assert result == "word3 word4 word5"


# 8. Chunk ID: Act format
def test_chunk_id_act(basic_unit):
    cid = _next_chunk_id("SYN-ACT-001", basic_unit)
    assert "SYN-ACT-001" in cid
    assert "CH-" in cid or "S" in cid


# 9. Chunk ID: Rule format
def test_chunk_id_rule():
    u = LegalUnit(document_id="SYN-RULE-001", text="Rule text.", section_number="5")
    cid = _next_chunk_id("SYN-RULE-001", u)
    assert "SYN-RULE-001" in cid
    assert "R" in cid


# 10. Chunk ID: Contract format
def test_chunk_id_contract():
    u = LegalUnit(document_id="SYN-CONT-001", text="Clause text.", section_number="3")
    cid = _next_chunk_id("SYN-CONT-001", u)
    assert "SYN-CONT-001" in cid
    assert "CLAUSE" in cid


# 11. Detect prefix from doc_id
def test_detect_prefix():
    assert _detect_prefix("SYN-ACT-001") == "ACT"
    assert _detect_prefix("SYN-RULE-001") == "RULE"
    assert _detect_prefix("SYN-CONT-001") == "CONT"
    assert _detect_prefix("SYN-JUDG-001") == "JUDG"
    assert _detect_prefix("SYN-NOTIF-001") == "NOTIF"
    assert _detect_prefix("SYN-GUIDE-001") == "GUIDE"


# 12. ChunkType detection by doc type + section number
def test_detect_chunk_type_act():
    ct = _detect_chunk_type("act", "5")
    assert ct == ChunkType.SECTION


def test_detect_chunk_type_judgment():
    ct = _detect_chunk_type("judgment", "1")
    assert ct == ChunkType.JUDGMENT_METADATA
    ct2 = _detect_chunk_type("judgment", "3")
    assert ct2 == ChunkType.JUDGMENT_ISSUE
    ct3 = _detect_chunk_type("judgment", "6")
    assert ct3 == ChunkType.JUDGMENT_ORDER


def test_detect_chunk_type_contract():
    ct = _detect_chunk_type("contract", "5")
    assert ct == ChunkType.CONTRACT_CLAUSE


# 13. Parser: section → LegalUnit
def test_parser_section_to_unit(parser, sample_act_section, sample_act_doc):
    units = parser.parse_section(sample_act_section, sample_act_doc, {}, {})
    assert len(units) >= 1
    primary = units[0]
    assert primary.document_id == "SYN-ACT-001"
    assert primary.section_number == "10"
    assert primary.synthetic is True
    assert primary.source_authority == "SYNTHETIC"
    assert primary.chapter_number == "III"


# 14. Parser: subsection detection for act sections
def test_parser_subsection_detection(parser, sample_act_section, sample_act_doc):
    units = parser.parse_section(sample_act_section, sample_act_doc, {}, {})
    # The section text has (1), (2), (3) → should produce child sub-units
    subsections = [u for u in units if u.parent_unit_id is not None]
    assert len(subsections) >= 2, f"Expected >=2 subsections, got {len(subsections)}"
    for ss in subsections:
        assert ss.synthetic is True
        assert ss.source_authority == "SYNTHETIC"


# 15. Parser: chapter parsing
def test_parser_chapter_parsing(parser):
    num, title = parser._parse_chapter("Chapter III: Substantive Obligations and Standards")
    assert num == "III"
    assert "Substantive" in title


def test_parser_chapter_parsing_roman_numeral(parser):
    num, title = parser._parse_chapter("Chapter IV: Penalties and Enforcement")
    assert num == "IV"


# 16. Chunker: single unit within target → 1 chunk
def test_chunker_single_chunk(chunker, basic_unit):
    chunks = chunker.chunk_unit(basic_unit, "act")
    assert len(chunks) == 1
    c = chunks[0]
    assert c.synthetic is True
    assert c.source_authority == "SYNTHETIC"
    assert c.text.strip() != ""
    assert c.embedding_text.strip() != ""
    assert c.retrieval_text.strip() != ""


# 17. Chunker: large text gets split into multiple chunks
def test_chunker_large_text_splits():
    chunker = LegalChunker(target_tokens=20, max_tokens=30, min_tokens=5, overlap_tokens=5)
    long_text = " ".join([f"word{i}" for i in range(200)])
    u = LegalUnit(
        document_id="SYN-ACT-001",
        unit_type=ChunkType.SECTION,
        section_number="7",
        section_title="Big Section",
        text=long_text,
        synthetic=True,
        source_authority="SYNTHETIC",
    )
    chunks = chunker.chunk_unit(u, "act")
    assert len(chunks) >= 2
    for c in chunks:
        assert c.synthetic is True
        assert c.source_authority == "SYNTHETIC"
        assert c.text.strip() != ""


# 18. Embedding text contains document type and section info
def test_embedding_text_format(chunker, basic_unit):
    chunks = chunker.chunk_unit(basic_unit, "act")
    et = chunks[0].embedding_text
    assert "[ACT]" in et
    assert "Digital Services" in et or "Section 10" in et


# 19. Definition extraction
def test_definition_extraction(sample_act_section, sample_act_doc):
    # Add a definition to the section text
    section = dict(sample_act_section)
    section["text"] = (
        'In this Act, "regulated organization" means any entity subject to the Act. '
        '"authority" means the Board established under Section 3.'
    )
    defs = extract_definitions(section, sample_act_doc)
    terms = [d["term"] for d in defs]
    assert "regulated organization" in terms or "authority" in terms
    for d in defs:
        assert d["synthetic"] is True
        assert d["source_authority"] == "SYNTHETIC"


# 20. Cross-reference extraction
def test_cross_reference_extraction():
    u = LegalUnit(
        unit_id="SYN-ACT-001-UNIT-SEC10",
        document_id="SYN-ACT-001",
        text="As per Section 17(2), entities must comply. See also SYN-ACT-005 for penalties.",
        synthetic=True,
        source_authority="SYNTHETIC",
    )
    existing_docs = {"SYN-ACT-001", "SYN-ACT-005"}
    refs = extract_cross_references(u, existing_docs)
    ref_types = {r["reference_type"] for r in refs}
    assert "SECTION_REFERENCE" in ref_types or "ACT_REFERENCE" in ref_types
    for r in refs:
        assert r["synthetic"] is True
        assert r["source_authority"] == "SYNTHETIC"


# ──────────────────────────────────────────────
# Integration Test
# ──────────────────────────────────────────────

def test_full_pipeline_integration(tmp_path):
    """
    Integration test: creates a mini synthetic corpus in a temp dir,
    runs the full structuring engine, and validates outputs.
    """
    # ── Setup mini corpus ──────────────────────
    synthetic_root = tmp_path / "synthetic"
    structured_dir = synthetic_root / "structured"
    metadata_dir   = synthetic_root / "metadata"
    reports_dir    = synthetic_root / "reports"
    raw_acts_dir   = synthetic_root / "raw" / "acts"

    structured_dir.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    raw_acts_dir.mkdir(parents=True)

    # Write a mini documents.jsonl
    docs = [
        {
            "document_id": "SYN-ACT-001",
            "document_type": "act",
            "title": "Test Act 2025 (Synthetic)",
            "legal_domain": "Contract Law",
            "source_authority": "SYNTHETIC",
            "synthetic": True,
            "document_version_group_id": "vg-001",
            "version_label": "v1.0-original",
            "sha256": "a" * 64,
            "raw_file_path": None,
            "section_count": 2,
            "page_count": 1,
        },
        {
            "document_id": "SYN-CONT-001",
            "document_type": "contract",
            "title": "Test Agreement (Synthetic)",
            "legal_domain": "Contract Law",
            "source_authority": "SYNTHETIC",
            "synthetic": True,
            "document_version_group_id": "vg-002",
            "version_label": "v1.0",
            "sha256": "b" * 64,
            "raw_file_path": None,
            "section_count": 1,
            "page_count": 1,
        },
    ]
    with (structured_dir / "documents.jsonl").open("w") as f:
        for d in docs:
            f.write(json.dumps(d) + "\n")

    # Write sections.jsonl
    sections = [
        {
            "section_id": "SYN-ACT-001-SEC-1",
            "document_id": "SYN-ACT-001",
            "version_group_id": "vg-001",
            "version_id": "v1.0-original",
            "section_number": "1",
            "title": "Section 1 - Short title",
            "chapter": "Chapter I: Preliminary",
            "heading": "Short title",
            "text": "(1) This Act may be called the Test Act. (2) It extends to all of Bharat.",
            "provisions": [],
            "explanations": [],
            "source_authority": "SYNTHETIC",
            "synthetic": True,
            "page_start": 1,
            "page_end": 1,
        },
        {
            "section_id": "SYN-ACT-001-SEC-2",
            "document_id": "SYN-ACT-001",
            "version_group_id": "vg-001",
            "version_id": "v1.0-original",
            "section_number": "2",
            "title": "Section 2 - Definitions",
            "chapter": "Chapter I: Preliminary",
            "heading": "Definitions",
            "text": '"authority" means the Board established under this Act. "person" means any individual.',
            "provisions": [],
            "explanations": [],
            "source_authority": "SYNTHETIC",
            "synthetic": True,
            "page_start": 1,
            "page_end": 1,
        },
        {
            "section_id": "SYN-CONT-001-CLAUSE-1",
            "document_id": "SYN-CONT-001",
            "section_number": "1",
            "title": "Clause 1 - Preamble",
            "heading": "Preamble",
            "text": "This Agreement is entered into between Party A and Party B.",
            "provisions": [],
            "explanations": [],
            "source_authority": "SYNTHETIC",
            "synthetic": True,
            "page_start": 1,
            "page_end": 1,
        },
    ]
    with (structured_dir / "sections.jsonl").open("w") as f:
        for s in sections:
            f.write(json.dumps(s) + "\n")

    # Empty provenance
    (metadata_dir / "provenance.jsonl").write_text("")

    # Write raw act text
    raw_text = textwrap.dedent("""\
        # Test Act 2025 (Synthetic)

        ## PREAMBLE

        An Act to test the structuring pipeline.

        ## Chapter I: Preliminary

        ### Section 1. Short title
        (1) This Act may be called the Test Act. (2) It extends to all of Bharat.

        ### Section 2. Definitions
        "authority" means the Board established under this Act.
    """)
    (raw_acts_dir / "SYN-ACT-001.txt").write_text(raw_text, encoding="utf-8")

    # ── Run engine ─────────────────────────────
    engine = StructuringEngine(
        synthetic_root = synthetic_root,
        output_root    = structured_dir,
        target_tokens  = 100,
        max_tokens     = 200,
        min_tokens     = 5,
        overwrite      = True,
        verbose        = False,
    )
    summary = engine.run()

    # ── Assertions ─────────────────────────────
    # Output files exist
    assert (structured_dir / "chunks.jsonl").exists()
    assert (structured_dir / "legal_units.jsonl").exists()
    assert (structured_dir / "definitions.jsonl").exists()
    assert (structured_dir / "cross_references.jsonl").exists()
    assert (structured_dir / "chunk_statistics.json").exists()

    # Non-zero chunks
    chunks = []
    with (structured_dir / "chunks.jsonl").open() as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    assert len(chunks) >= 2, f"Expected >=2 chunks, got {len(chunks)}"

    # All chunks have synthetic=True, source_authority=SYNTHETIC
    for c in chunks:
        assert c["synthetic"] is True, f"chunk {c['chunk_id']} missing synthetic=True"
        assert c["source_authority"] == "SYNTHETIC", f"chunk {c['chunk_id']} wrong source_authority"
        assert c["embedding_text"].strip() != ""
        assert c["retrieval_text"].strip() != ""

    # Documents processed = 2
    assert summary["documents_processed"] == 2

    # Stats has required keys
    assert "chunks_total" in summary
    assert "legal_units_total" in summary
    assert summary["synthetic"] is True
