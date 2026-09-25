"""
pipeline/structuring/models.py
==============================
Data models for Phase 3: Legal Document Structuring & Chunking.

Defines:
  - ChunkType         : Enum of all legal unit / chunk types
  - LegalUnit         : Normalized internal representation of a legal structural node
  - ChunkRecord       : Final retrieval chunk with provenance chain
  - DefinitionRecord  : Extracted legal term definition
  - CrossReferenceRecord : Extracted internal/external reference
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Chunk Type Enumeration
# ──────────────────────────────────────────────

class ChunkType(str, Enum):
    # Legislation
    PREAMBLE           = "PREAMBLE"
    CHAPTER            = "CHAPTER"
    SECTION            = "SECTION"
    SUBSECTION         = "SUBSECTION"
    CLAUSE             = "CLAUSE"
    PROVISO            = "PROVISO"
    EXPLANATION        = "EXPLANATION"
    DEFINITION         = "DEFINITION"
    SCHEDULE           = "SCHEDULE"
    ANNEXURE           = "ANNEXURE"
    # Rules / Regulations
    RULE               = "RULE"
    SUB_RULE           = "SUB_RULE"
    REGULATION         = "REGULATION"
    # Notifications / Circulars
    NOTIFICATION       = "NOTIFICATION"
    NOTIFICATION_PARA  = "NOTIFICATION_PARA"
    # Guidance
    GUIDANCE_SECTION   = "GUIDANCE_SECTION"
    # Judgments
    JUDGMENT_METADATA  = "JUDGMENT_METADATA"
    JUDGMENT_FACTS     = "JUDGMENT_FACTS"
    JUDGMENT_ISSUE     = "JUDGMENT_ISSUE"
    JUDGMENT_ARGUMENT  = "JUDGMENT_ARGUMENT"
    JUDGMENT_REASONING = "JUDGMENT_REASONING"
    JUDGMENT_FINDING   = "JUDGMENT_FINDING"
    JUDGMENT_ORDER     = "JUDGMENT_ORDER"
    # Contracts
    CONTRACT_CLAUSE    = "CONTRACT_CLAUSE"
    CONTRACT_SCHEDULE  = "CONTRACT_SCHEDULE"
    # Generic
    PARAGRAPH          = "PARAGRAPH"
    OTHER              = "OTHER"


# Mapping judgment section numbers to chunk types
JUDGMENT_SECTION_MAP: Dict[str, ChunkType] = {
    "1": ChunkType.JUDGMENT_METADATA,
    "2": ChunkType.JUDGMENT_FACTS,
    "3": ChunkType.JUDGMENT_ISSUE,
    "4": ChunkType.JUDGMENT_ARGUMENT,
    "5": ChunkType.JUDGMENT_REASONING,
    "6": ChunkType.JUDGMENT_ORDER,
}

# ──────────────────────────────────────────────
# Legal Unit Model
# ──────────────────────────────────────────────

class LegalUnit(BaseModel):
    """
    Normalized internal representation of one legal structural node.
    Represents any level of the hierarchy: Chapter, Section, Subsection, Clause, etc.
    """

    # Identity
    unit_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    version_group_id: Optional[str] = None
    version_id: Optional[str] = None

    # Type
    unit_type: ChunkType = ChunkType.SECTION

    # Structural position
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    subsection_number: Optional[str] = None
    clause_number: Optional[str] = None

    # Hierarchy
    parent_unit_id: Optional[str] = None
    child_unit_ids: List[str] = Field(default_factory=list)

    # Content
    heading: Optional[str] = None
    text: str = ""
    provisions: List[str] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)

    # Page provenance
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    # Legal domain
    legal_domain: Optional[str] = None
    secondary_domains: List[str] = Field(default_factory=list)

    # Document metadata (denormalized for retrieval)
    document_title: Optional[str] = None
    act_year: Optional[int] = None
    jurisdiction: Optional[str] = None

    # Source provenance
    source_document_id: str = ""
    source_sha256: Optional[str] = None
    provenance_id: Optional[str] = None
    local_file: Optional[str] = None

    # Guardrails
    synthetic: bool = True
    source_authority: str = "SYNTHETIC"

    # Token estimate (computed later)
    estimated_tokens: Optional[int] = None


# ──────────────────────────────────────────────
# Chunk Record Model
# ──────────────────────────────────────────────

class ChunkRecord(BaseModel):
    """
    Final retrieval chunk record.
    Stored in legal-data/synthetic/structured/chunks.jsonl
    """

    # Identity
    chunk_id: str
    document_id: str
    version_group_id: Optional[str] = None
    version_id: Optional[str] = None

    # Type
    chunk_type: ChunkType

    # Document context (denormalized for search)
    title: Optional[str] = None

    # Structural position
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    subsection_number: Optional[str] = None
    clause_number: Optional[str] = None

    # Hierarchy
    parent_unit_id: Optional[str] = None
    source_unit_id: Optional[str] = None    # The LegalUnit this came from

    # Content
    text: str

    # Retrieval texts
    embedding_text: str = ""   # context-enriched for semantic search
    retrieval_text: str = ""   # identifier-preserving for BM25

    # Page provenance
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    # Sizing
    token_count: int = 0
    char_count: int = 0
    word_count: int = 0

    # Guardrails
    synthetic: bool = True
    source_authority: str = "SYNTHETIC"

    # Provenance chain
    source_document_id: Optional[str] = None
    source_sha256: Optional[str] = None
    provenance_id: Optional[str] = None
    local_file: Optional[str] = None

    # Domain
    legal_domains: List[str] = Field(default_factory=list)

    # Split metadata
    is_split: bool = False      # True if this chunk is part of a larger unit split
    split_index: Optional[int] = None
    split_total: Optional[int] = None


# ──────────────────────────────────────────────
# Definition Record Model
# ──────────────────────────────────────────────

class DefinitionRecord(BaseModel):
    """
    An extracted legal term definition.
    Stored in legal-data/synthetic/structured/definitions.jsonl
    """

    definition_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    version_id: Optional[str] = None
    term: str
    definition_text: str
    source_section_id: Optional[str] = None
    source_unit_id: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    synthetic: bool = True
    source_authority: str = "SYNTHETIC"


# ──────────────────────────────────────────────
# Cross-Reference Record Model
# ──────────────────────────────────────────────

class CrossReferenceRecord(BaseModel):
    """
    An extracted cross-reference within or across documents.
    Stored in legal-data/synthetic/structured/cross_references.jsonl
    """

    reference_id: str = Field(default_factory=lambda: str(uuid4()))
    source_unit_id: str
    source_document_id: str
    target_reference: str       # Raw text of the reference, e.g. "Section 17(2)"
    reference_type: str         # SECTION_REFERENCE, RULE_REFERENCE, ARTICLE_REFERENCE, etc.
    resolved_target_unit_id: Optional[str] = None   # null if not resolvable
    resolved_target_document_id: Optional[str] = None
    confidence: float = 1.0
    synthetic: bool = True
    source_authority: str = "SYNTHETIC"
