"""
pipeline/safety/service.py
==========================
Master Safety, Grounding & Citation Audit Service Facade for LegalLens Phase 7.
Coordinates Citation Verification, NLI Claim Grounding, Hallucination Detection,
Prompt Injection Defense, and Normative Source Authority Validation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from pipeline.legal_ai.context_builder import BuiltContext
from pipeline.legal_ai.models import Claim, LegalAIResponse
from pipeline.retrieval.models import RetrievedEvidence

from .citation_verifier import CitationVerifier
from .config import SafetyConfig, get_safety_config
from .grounding_engine import GroundingEngine
from .guardrails import SafetyGuardrails
from .hallucination_detector import HallucinationDetector
from .models import (
    CitationVerificationResult,
    CitationVerificationStatus,
    ClaimVerificationResult,
    EntailmentStatus,
    HallucinationFlag,
    SafetyAuditResult,
)
from .source_authority import SourceAuthorityVerifier


class SafetyService:
    """
    Central safety and grounding verification service for LegalLens.
    """

    def __init__(
        self,
        citation_verifier: Optional[CitationVerifier] = None,
        grounding_engine: Optional[GroundingEngine] = None,
        hallucination_detector: Optional[HallucinationDetector] = None,
        guardrails: Optional[SafetyGuardrails] = None,
        authority_verifier: Optional[SourceAuthorityVerifier] = None,
        config: Optional[SafetyConfig] = None,
    ):
        self.config = config or get_safety_config()
        self.citation_verifier = citation_verifier or CitationVerifier(config=self.config)
        self.grounding_engine = grounding_engine or GroundingEngine(config=self.config)
        self.hallucination_detector = hallucination_detector or HallucinationDetector(
            citation_verifier=self.citation_verifier,
            config=self.config,
        )
        self.guardrails = guardrails or SafetyGuardrails(config=self.config)
        self.authority_verifier = authority_verifier or SourceAuthorityVerifier()

    def audit_response(
        self,
        response: LegalAIResponse,
        context: Optional[BuiltContext] = None,
        evidence_items: Optional[List[RetrievedEvidence]] = None,
    ) -> SafetyAuditResult:
        """
        Execute comprehensive multi-vector safety, grounding, and citation audit on an AI response.
        """
        evidence_map: Dict[str, RetrievedEvidence] = {}
        if context and hasattr(context, "evidence_map"):
            evidence_map.update(context.evidence_map)
        elif "_evidence_context" in response.structured_data:
            for eid, ev_data in response.structured_data["_evidence_context"].items():
                if isinstance(ev_data, dict):
                    evidence_map[eid] = RetrievedEvidence(**ev_data)
        if evidence_items:
            for i, ev in enumerate(evidence_items, 1):
                evidence_map[f"E{i}"] = ev

        full_response_text = f"{response.direct_answer or ''} {str(response.structured_data)}"

        # 1. Formal Citation Verification
        raw_citations = list(response.evidence_refs)
        verified_citations = self.citation_verifier.verify_all_citations(
            citations=raw_citations,
            text_content=full_response_text,
            evidence_map=evidence_map,
        )

        # Calculate citation precision and recall
        if verified_citations:
            valid_cits = sum(
                1 for c in verified_citations
                if c.status in (CitationVerificationStatus.VERIFIED, CitationVerificationStatus.SUPERSEDED_VERSION)
            )
            citation_precision = round(valid_cits / len(verified_citations), 3)
        else:
            citation_precision = 1.0 if not raw_citations else 0.0

        citation_recall = 1.0 if (not evidence_map or raw_citations) else 0.5

        # 2. Claim Grounding & NLI Verification
        verified_claims, faithfulness_score, contradiction_score = self.grounding_engine.verify_all_claims(
            claims=response.claims,
            evidence_map=evidence_map,
        )

        # 3. Hallucination Detection & Scanning
        hallucinations = self.hallucination_detector.scan_response(
            response_text=full_response_text,
            citations=verified_citations,
            claims=verified_claims,
            evidence_map=evidence_map,
        )

        # 4. Prompt Injection & Advice Guardrails Scan
        has_advice_violation, advice_violations = self.guardrails.scan_output_for_advice(full_response_text)
        has_inj_violation, inj_violations = self.guardrails.scan_input_for_injection(full_response_text)

        all_violations = []
        if has_advice_violation:
            for v in advice_violations:
                all_violations.append({"type": "UNAUTHORIZED_LEGAL_ADVICE", "detail": v})
        if has_inj_violation:
            all_violations.extend(inj_violations)

        # 5. Source Authority Assessment
        authority_assessment = self.authority_verifier.evaluate_authority_bundle(
            list(evidence_map.values())
        )

        # 6. Audit Verdict Determination
        is_safe = True
        recommendations: List[str] = []

        critical_hallucinations = [h for h in hallucinations if h.severity == "CRITICAL"]

        if critical_hallucinations or has_inj_violation:
            audit_verdict = "REJECTED_UNSAFE"
            is_safe = False
            recommendations.append("Response contains critical hallucinations or security payloads. Reject release.")
        elif (
            faithfulness_score < self.config.min_faithfulness_score
            or citation_precision < self.config.min_citation_precision
            or any(h.severity == "HIGH" for h in hallucinations)
            or has_advice_violation
        ):
            audit_verdict = "NEEDS_REVIEW"
            is_safe = True
            recommendations.append("Response has grounding deficits or warnings. Human legal review recommended.")
        else:
            audit_verdict = "APPROVED"
            recommendations.append("Response meets all strict grounding, citation, and safety standards.")

        if authority_assessment.get("has_synthetic_sources"):
            recommendations.append("CORPUS TRANSPARENCY: Verified synthetic development origin.")

        return SafetyAuditResult(
            is_safe=is_safe,
            audit_verdict=audit_verdict,
            faithfulness_score=faithfulness_score,
            citation_precision=citation_precision,
            citation_recall=citation_recall,
            hallucination_count=len(hallucinations),
            citations_verified=verified_citations,
            claims_verified=verified_claims,
            hallucinations_detected=hallucinations,
            safety_violations=all_violations,
            recommendations=recommendations,
            disclaimer_present=bool(response.disclaimer),
            synthetic_dataset_flag=response.synthetic,
        )

    def sanitize_input(self, text: str) -> str:
        """Sanitize query or uploaded document text from prompt injection attacks."""
        return self.guardrails.sanitize_input(text)

    def scan_input(self, text: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Check user input for injection or security risks."""
        return self.guardrails.scan_input_for_injection(text)
