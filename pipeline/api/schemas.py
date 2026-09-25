"""
pipeline/api/schemas.py
=======================
Pydantic schemas for the LegalLens FastAPI REST API layer.
Provides strong typing for all frontend-backend interactions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResponseStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    LIMITED_EVIDENCE = "LIMITED_EVIDENCE"
    NO_EVIDENCE = "NO_EVIDENCE"
    CONFLICT = "CONFLICT"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class LegalHierarchyNode(BaseModel):
    id: str
    title: str
    type: str  # chapter | section | subsection | clause
    chunk_id: Optional[str] = None
    page: Optional[int] = None
    children: List[LegalHierarchyNode] = Field(default_factory=list)


class DocumentSummaryResponse(BaseModel):
    document_id: str
    title: str
    document_type: str = "Act"
    chunk_count: int = 0
    page_count: int = 1
    source_authority: str = "SYNTHETIC"
    synthetic: bool = True
    sha256: Optional[str] = None
    version_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DocumentDetailResponse(BaseModel):
    document_id: str
    title: str
    document_type: str = "Act"
    chunk_count: int = 0
    page_count: int = 1
    source_authority: str = "SYNTHETIC"
    synthetic: bool = True
    sha256: Optional[str] = None
    version_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    hierarchy: List[LegalHierarchyNode] = Field(default_factory=list)
    raw_text: Optional[str] = None
    summary: Optional[str] = None
    disclaimer: str = "Synthetic development source — this document is fictional test data and should not be treated as real law."


class ChunkResponse(BaseModel):
    chunk_id: str
    document_id: str
    chapter: Optional[str] = None
    section: Optional[str] = None
    subsection: Optional[str] = None
    title: Optional[str] = None
    text: str
    page_start: Optional[int] = 1
    page_end: Optional[int] = 1
    source_authority: str = "SYNTHETIC"
    synthetic: bool = True
    content_hash: Optional[str] = None


class DocumentUploadRequest(BaseModel):
    title: str
    document_type: str = "Contract"
    text_content: str
    source_authority: str = "USER_DOCUMENT"
    synthetic: bool = True


class RetrieveRequest(BaseModel):
    query: str
    document_id: Optional[str] = None
    top_k: int = 5
    legal_domain: Optional[str] = None


class RetrievedEvidenceItem(BaseModel):
    chunk_id: str
    document_id: str
    section: Optional[str] = None
    title: Optional[str] = None
    text: str
    score: float = 0.0
    page_start: Optional[int] = 1
    page_end: Optional[int] = 1
    source_authority: str = "SYNTHETIC"
    synthetic: bool = True


class RetrieveResponse(BaseModel):
    query: str
    results: List[RetrievedEvidenceItem] = Field(default_factory=list)
    total_results: int = 0


class ClaimItem(BaseModel):
    claim_id: str
    text: str
    claim_type: str = "LEGAL_PROVISION"
    evidence_refs: List[str] = Field(default_factory=list)
    support_status: str = "SUPPORTED"


class CitationItem(BaseModel):
    citation_id: str
    document_id: str
    section: Optional[str] = None
    page: Optional[int] = 1
    source_authority: str = "SYNTHETIC"
    synthetic: bool = True
    excerpt: Optional[str] = None
    sha256: Optional[str] = None
    is_valid: bool = True
    hash_matched: bool = True


class AIAnswerRequest(BaseModel):
    query: str
    document_id: Optional[str] = None
    user_facts: Optional[List[Dict[str, str]]] = None
    top_k: int = 5


class AIResponse(BaseModel):
    task_type: str
    query: str
    direct_answer: Optional[str] = ""
    status: ResponseStatus = ResponseStatus.VERIFIED
    confidence: float = 0.95
    claims: List[ClaimItem] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)
    evidence_items: List[RetrievedEvidenceItem] = Field(default_factory=list)
    contradictions_detected: List[str] = Field(default_factory=list)
    synthetic_sources_used: bool = True
    safety_flags: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "LegalLens provides AI-assisted legal information and document analysis. It is not a substitute for professional legal advice."


class AISummarizeRequest(BaseModel):
    document_id: Optional[str] = None
    document_text: Optional[str] = None
    query: str = "Summarize this legal document"


class AISimplifyRequest(BaseModel):
    text: str
    document_id: Optional[str] = None
    query: str = "Explain and simplify this legal text in plain English"


class AIClauseAnalysisRequest(BaseModel):
    clause_text: str
    document_id: Optional[str] = None
    query: str = "Analyze this legal clause for obligations, rights, and risks"


class AICompareRequest(BaseModel):
    doc_a_id: Optional[str] = None
    doc_b_id: Optional[str] = None
    doc_a_text: Optional[str] = None
    doc_b_text: Optional[str] = None
    query: str = "Compare these two contract versions and identify differences"


class AIObligationsRequest(BaseModel):
    document_id: Optional[str] = None
    document_text: Optional[str] = None
    query: str = "Extract all mandatory legal obligations from this document"


class AIDeadlinesRequest(BaseModel):
    document_id: Optional[str] = None
    document_text: Optional[str] = None
    query: str = "Extract all legal deadlines and timelines from this document"


class AIVerifyRequest(BaseModel):
    claim_text: str
    cited_evidence_ids: List[str] = Field(default_factory=list)


class ActivityEvent(BaseModel):
    event_id: str
    event_type: str
    title: str
    description: str
    timestamp: str
    document_id: Optional[str] = None
    badge: Optional[str] = None


class DashboardStatsResponse(BaseModel):
    total_documents: int = 0
    total_analyses: int = 0
    pending_actions: int = 0
    recent_documents: List[DocumentSummaryResponse] = Field(default_factory=list)
    recent_activity: List[ActivityEvent] = Field(default_factory=list)


class SourceItem(BaseModel):
    source_id: str
    source_name: str
    source_authority: str
    document_type: str
    total_documents: int
    total_chunks: int
    synthetic: bool = True
    disclaimer: str = "Synthetic development source — fictional test data."
