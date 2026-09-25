"""
pipeline/safety/models.py
=========================
Pydantic data models for Phase 7: Grounding, Citation Verification,
Hallucination Detection, and Safety Guardrails.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CitationVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNRESOLVED = "UNRESOLVED"
    FABRICATED = "FABRICATED"
    SUPERSEDED_VERSION = "SUPERSEDED_VERSION"
    AMBIGUOUS = "AMBIGUOUS"


class CitationVerificationResult(BaseModel):
    """
    Formal verification of an individual legal citation against stored KB chunks & provenance.
    """
    citation_id: str = Field(default_factory=lambda: f"cit-{uuid4().hex[:6]}")
    raw_citation: str
    status: CitationVerificationStatus
    resolved_chunk_id: Optional[str] = None
    resolved_document_id: Optional[str] = None
    resolved_section: Optional[str] = None
    source_sha256: Optional[str] = None
    provenance_id: Optional[str] = None
    source_authority: str = "SYNTHETIC"
    is_synthetic: bool = True
    is_version_current: bool = True
    formatted_legal_citation: Optional[str] = None
    verification_notes: List[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status in (CitationVerificationStatus.VERIFIED, CitationVerificationStatus.SUPERSEDED_VERSION)

    @property
    def hash_matched(self) -> bool:
        return bool(self.source_sha256)

    @property
    def document_id(self) -> Optional[str]:
        return self.resolved_document_id

    @property
    def section(self) -> Optional[str]:
        return self.resolved_section

    @property
    def sha256(self) -> Optional[str]:
        return self.source_sha256

    @property
    def synthetic(self) -> bool:
        return self.is_synthetic

    @property
    def excerpt(self) -> Optional[str]:
        return self.formatted_legal_citation or self.raw_citation


class EntailmentStatus(str, Enum):
    ENTAILED = "ENTAILED"
    PARTIALLY_ENTAILED = "PARTIALLY_ENTAILED"
    CONTRADICTED = "CONTRADICTED"
    UNGROUNDED = "UNGROUNDED"


class ClaimVerificationResult(BaseModel):
    """
    NLI and Grounding entailment result for an atomic legal claim against cited evidence.
    """
    claim_id: str
    claim_text: str
    status: EntailmentStatus
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    entailment_confidence: float = 1.0
    lexical_overlap_ratio: float = 1.0
    contradiction_notes: Optional[str] = None


class HallucinationType(str, Enum):
    FABRICATED_SECTION = "FABRICATED_SECTION"
    NON_EXISTENT_STATUTE = "NON_EXISTENT_STATUTE"
    FABRICATED_PENALTY = "FABRICATED_PENALTY"
    VERSION_ANACHRONISM = "VERSION_ANACHRONISM"
    CONTRADICTORY_ASSERTION = "CONTRADICTORY_ASSERTION"
    UNSUPPORTED_EXTRAPOLATION = "UNSUPPORTED_EXTRAPOLATION"


class HallucinationFlag(BaseModel):
    """
    Detected hallucination instance with severity and remediation strategy.
    """
    flag_id: str = Field(default_factory=lambda: f"hal-{uuid4().hex[:6]}")
    hallucination_type: HallucinationType
    flagged_text: str
    severity: str = "HIGH"  # CRITICAL | HIGH | MEDIUM | LOW
    explanation: str
    mitigation_action: str = "FLAG"  # REDACT | WARN | FLAG | REWRITE


class SafetyViolationType(str, Enum):
    PROMPT_INJECTION = "PROMPT_INJECTION"
    JAILBREAK = "JAILBREAK"
    UNAUTHORIZED_LEGAL_ADVICE = "UNAUTHORIZED_LEGAL_ADVICE"
    UNBOUNDED_LIABILITY_GUARANTEE = "UNBOUNDED_LIABILITY_GUARANTEE"
    CONFIDENTIAL_EXFILTRATION = "CONFIDENTIAL_EXFILTRATION"


class SafetyAuditResult(BaseModel):
    """
    Comprehensive audit-grade verification artifact assessing an AI response.
    """
    audit_id: str = Field(default_factory=lambda: f"audit-{uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    is_safe: bool = True
    audit_verdict: str = "APPROVED"  # APPROVED | NEEDS_REVIEW | REJECTED_UNSAFE
    faithfulness_score: float = 1.0
    citation_precision: float = 1.0
    citation_recall: float = 1.0
    hallucination_count: int = 0
    citations_verified: List[CitationVerificationResult] = Field(default_factory=list)
    claims_verified: List[ClaimVerificationResult] = Field(default_factory=list)
    hallucinations_detected: List[HallucinationFlag] = Field(default_factory=list)
    safety_violations: List[Dict[str, Any]] = Field(default_factory=list)
    disclaimer_present: bool = True
    synthetic_dataset_flag: bool = True

    @property
    def is_blocked(self) -> bool:
        return not self.is_safe or self.audit_verdict == "REJECTED_UNSAFE"

    @property
    def verified_citations(self) -> List[CitationVerificationResult]:
        return self.citations_verified

    @property
    def hallucination_flags(self) -> List[HallucinationFlag]:
        return self.hallucinations_detected
