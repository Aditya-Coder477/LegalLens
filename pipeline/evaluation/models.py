"""
pipeline/evaluation/models.py
=============================
Canonical data models for Phase 8: Evaluation, Benchmarking & Security Testing.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class SecuritySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class QualityGateStatus(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


class EvaluationLayer(str, Enum):
    CORPUS_QUALITY = "corpus_quality"
    RETRIEVAL_QUALITY = "retrieval_quality"
    EVIDENCE_QUALITY = "evidence_quality"
    AI_ANSWER_QUALITY = "ai_answer_quality"
    GROUNDING_FAITHFULNESS = "grounding_faithfulness"
    CITATION_INTEGRITY = "citation_integrity"
    SAFETY_SECURITY = "safety_security"
    PERFORMANCE_LATENCY = "performance_latency"


class EvaluationCategory(str, Enum):
    RETRIEVAL = "retrieval_eval"
    MULTI_HOP = "multi_hop_eval"
    CROSS_REFERENCE = "cross_reference_eval"
    DEFINITION = "definition_eval"
    GROUNDED_QA = "grounded_qa"
    UNANSWERABLE_QA = "unanswerable_qa"
    CONTRADICTION_QA = "contradiction_qa"
    VERSION_QA = "version_qa"
    SUMMARY = "summary_eval"
    CLAUSE_ANALYSIS = "clause_analysis_eval"
    OBLIGATION = "obligation_eval"
    COMPARISON = "comparison_eval"
    GROUNDING = "grounding_eval"
    CITATION = "citation_eval"
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    SECRET_LEAKAGE = "secret_leakage"
    PII_LEAKAGE = "pii_leakage"
    CROSS_TENANT = "cross_tenant"
    MALFORMED = "malformed_inputs"


class EvaluationCase(BaseModel):
    """Canonical test case schema for all evaluation categories."""
    case_id: str
    category: str
    subcategory: Optional[str] = None
    evaluation_layer: Optional[str] = None

    query: Optional[str] = None
    document_context: Optional[str] = None
    input_documents: List[str] = Field(default_factory=list)

    expected_chunk_ids: List[str] = Field(default_factory=list)
    expected_document_ids: List[str] = Field(default_factory=list)
    expected_documents: List[str] = Field(default_factory=list)
    expected_sections: List[str] = Field(default_factory=list)
    relevance_scores: Dict[str, int] = Field(default_factory=dict)  # Graded relevance: 0..3

    expected_answer: Optional[str] = None
    expected_claims: List[Dict[str, Any]] = Field(default_factory=list)
    expected_citations: List[str] = Field(default_factory=list)

    adversarial_type: Optional[str] = None
    expected_behavior: str = "SAFE"  # e.g. SAFE, ABSTAIN, CONFLICT_DETECTED
    difficulty: str = "MEDIUM"        # EASY | MEDIUM | HARD | ADVERSARIAL
    synthetic: bool = True
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        # Sync expected_documents and expected_document_ids
        if self.expected_document_ids and not self.expected_documents:
            self.expected_documents = list(self.expected_document_ids)
        elif self.expected_documents and not self.expected_document_ids:
            self.expected_document_ids = list(self.expected_documents)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvaluationCase:
        return cls(**data)


class EvaluationResult(BaseModel):
    """Individual execution outcome of an EvaluationCase."""
    run_id: str = Field(default_factory=lambda: f"RUN-{uuid4().hex[:6].upper()}")
    case_id: str
    category: str

    status: EvaluationStatus = EvaluationStatus.PASS

    metrics: Dict[str, Any] = Field(default_factory=dict)
    failures: List[Any] = Field(default_factory=list)
    latency_ms: float = 0.0

    details: Dict[str, Any] = Field(default_factory=dict)
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["status"] = self.status.value if isinstance(self.status, Enum) else str(self.status)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvaluationResult:
        if isinstance(data.get("status"), str):
            data["status"] = EvaluationStatus(data["status"])
        return cls(**data)


class SecurityFinding(BaseModel):
    """Recorded vulnerability or safety issue during security audits."""
    finding_id: str = Field(default_factory=lambda: f"SEC-{uuid4().hex[:6].upper()}")
    category: str
    severity: SecuritySeverity = SecuritySeverity.HIGH

    title: str
    description: str

    reproduction_steps: Optional[str] = None
    expected_behavior: str = ""
    actual_behavior: str = ""

    affected_component: Optional[str] = None
    test_case_id: Optional[str] = None

    evidence: Dict[str, Any] = Field(default_factory=dict)
    remediation: Optional[str] = None
    status: str = "OPEN"  # OPEN | FIXED | ACCEPTED_RISK | NOT_REPRODUCIBLE
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["severity"] = self.severity.value if isinstance(self.severity, Enum) else str(self.severity)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SecurityFinding:
        if isinstance(data.get("severity"), str):
            data["severity"] = SecuritySeverity(data["severity"])
        return cls(**data)


class QualityGateDimension(BaseModel):
    """Single metric or sub-dimension evaluated in the Quality Gate."""
    name: str
    metric_name: str
    actual_value: Any
    threshold: Any
    passed: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class QualityGateResult(BaseModel):
    """Machine-readable quality gate evaluation across all pipeline layers."""
    status: QualityGateStatus = QualityGateStatus.PASS
    passed: bool = True
    evaluated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    dimensions: List[QualityGateDimension] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["status"] = self.status.value if isinstance(self.status, Enum) else str(self.status)
        return d
