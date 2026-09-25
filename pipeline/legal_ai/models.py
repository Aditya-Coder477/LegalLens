"""
pipeline/legal_ai/models.py
===========================
Pydantic data models and schemas for Phase 6: Legal Reasoning & AI Features.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    LEGAL_QA = "LEGAL_QA"
    SUMMARY = "SUMMARY"
    SIMPLIFY = "SIMPLIFY"
    CLAUSE_ANALYSIS = "CLAUSE_ANALYSIS"
    COMPARE_DOCUMENTS = "COMPARE_DOCUMENTS"
    EXTRACT_OBLIGATIONS = "EXTRACT_OBLIGATIONS"
    EXTRACT_DEADLINES = "EXTRACT_DEADLINES"
    EXTRACT_RIGHTS_DUTIES = "EXTRACT_RIGHTS_DUTIES"
    IDENTIFY_ISSUES = "IDENTIFY_ISSUES"
    NEXT_STEPS = "NEXT_STEPS"
    CHECKLIST = "CHECKLIST"
    MULTI_DOCUMENT_ANALYSIS = "MULTI_DOCUMENT_ANALYSIS"


class ClaimType(str, Enum):
    FACT = "FACT"
    LEGAL_PROVISION = "LEGAL_PROVISION"
    OBLIGATION = "OBLIGATION"
    RIGHT = "RIGHT"
    DEFINITION = "DEFINITION"
    DEADLINE = "DEADLINE"
    INTERPRETATION = "INTERPRETATION"
    INFERENCE = "INFERENCE"
    USER_FACT = "USER_FACT"


class SupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class Claim(BaseModel):
    """
    Structured atomic legal statement mapped to evidence for grounding validation.
    """
    claim_id: str = Field(default_factory=lambda: f"C{uuid4().hex[:6]}")
    text: str
    claim_type: ClaimType = ClaimType.LEGAL_PROVISION
    evidence_refs: List[str] = Field(default_factory=list)
    support_status: SupportStatus = SupportStatus.SUPPORTED

    @property
    def citations(self) -> List[str]:
        return self.evidence_refs


class UserFact(BaseModel):
    """
    User-provided factual statement, explicitly segregated from authoritative law.
    """
    fact_id: str = Field(default_factory=lambda: f"UF{uuid4().hex[:4]}")
    text: str
    source: str = "USER_PROVIDED"


# ──────────────────────────────────────────────
# Structured Feature Outputs
# ──────────────────────────────────────────────

class LegalAnswer(BaseModel):
    """Grounded Legal Q&A structured response (Section 12)."""
    direct_answer: str
    key_points: List[str] = Field(default_factory=list)
    applicability: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    """Structured legal document summary (Section 17)."""
    overview: str
    purpose: str
    key_provisions: List[str] = Field(default_factory=list)
    rights: List[str] = Field(default_factory=list)
    obligations: List[str] = Field(default_factory=list)
    important_definitions: List[str] = Field(default_factory=list)
    deadlines: List[str] = Field(default_factory=list)
    penalties: List[str] = Field(default_factory=list)
    termination: Optional[str] = None
    dispute_resolution: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)


class SimplificationResult(BaseModel):
    """Plain-language simplification preserving legal conditions and exceptions (Section 19)."""
    simplified_text: str
    explained_terms: Dict[str, str] = Field(default_factory=dict)
    preserved_conditions: List[str] = Field(default_factory=list)
    preserved_exceptions: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class ClauseAnalysis(BaseModel):
    """Comprehensive single-clause / statutory provision analysis (Section 21)."""
    clause_type: str
    plain_language_meaning: str
    parties_or_actors: List[str] = Field(default_factory=list)
    obligations: List[str] = Field(default_factory=list)
    rights: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)
    deadlines: List[str] = Field(default_factory=list)
    potential_ambiguities: List[str] = Field(default_factory=list)
    questions_to_clarify: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    """Contract or statutory version comparison output (Section 32)."""
    overall_summary: str
    target_document_a: str
    target_document_b: str
    added_provisions: List[str] = Field(default_factory=list)
    removed_provisions: List[str] = Field(default_factory=list)
    modified_provisions: List[str] = Field(default_factory=list)
    unchanged_provisions: List[str] = Field(default_factory=list)
    conflicting_provisions: List[str] = Field(default_factory=list)
    obligation_changes: List[str] = Field(default_factory=list)
    deadline_changes: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class ObligationItem(BaseModel):
    """Extracted legal obligation (Section 24)."""
    actor: str
    action: str
    condition: Optional[str] = None
    deadline: Optional[str] = None
    source_clause: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)


class DeadlineItem(BaseModel):
    """Extracted deadline or date requirement (Section 25)."""
    deadline_type: str = "RELATIVE"  # RELATIVE | ABSOLUTE
    duration: Optional[str] = None
    trigger: Optional[str] = None
    actor: Optional[str] = None
    required_action: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)


class RightDutyItem(BaseModel):
    """Extracted right, duty, prohibition or permission (Section 27)."""
    type: str  # RIGHT | DUTY | OBLIGATION | PROHIBITION | PERMISSION
    actor: str
    action: str
    conditions: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class LegalIssueItem(BaseModel):
    """Detected legal risk or inconsistency (Section 28)."""
    issue_type: str
    description: str
    affected_provision: Optional[str] = None
    severity: str = "MEDIUM"  # HIGH | MEDIUM | LOW
    evidence_refs: List[str] = Field(default_factory=list)


class NextStepItem(BaseModel):
    """Actionable procedural step derived from evidence (Section 35)."""
    step_number: int
    action: str
    reason: str
    evidence_refs: List[str] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    """Item for compliance or document review checklist (Section 37)."""
    item: str
    reason: str
    source_provision: Optional[str] = None
    status: str = "PENDING"  # PENDING | COMPLIANT | NOT_APPLICABLE
    evidence_refs: List[str] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Master Legal AI Response
# ──────────────────────────────────────────────

class LegalAIResponse(BaseModel):
    """
    Canonical response wrapper for all Phase 6 AI features (Section 9).
    """
    request_id: str = Field(default_factory=lambda: f"req-{uuid4().hex[:8]}")
    task_type: TaskType
    status: str = "SUCCESS"  # SUCCESS | LOW_EVIDENCE | NO_EVIDENCE | ERROR
    direct_answer: Optional[str] = None
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    claims: List[Claim] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    synthetic: bool = True
    data_status: str = "SYNTHETIC_DEVELOPMENT_DATA"
    model: str = "legal-reasoner-v1"
    provider: str = "local"
    prompt_version: str = "v1.0"
    claim_support_rate: float = 1.0
    disclaimer: str = (
        "LegalLens provides evidence-grounded legal information only and is not a "
        "substitute for professional legal advice from an advocate or attorney."
    )
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def confidence(self) -> float:
        return self.claim_support_rate

    @property
    def contradictions_detected(self) -> List[str]:
        return self.structured_data.get("conflicting_provisions", self.structured_data.get("contradictions", []))

    @property
    def next_steps(self) -> List[str]:
        steps = self.structured_data.get("next_steps", [])
        if steps and isinstance(steps[0], dict):
            return [s.get("action", str(s)) for s in steps]
        return [str(s) for s in steps]
