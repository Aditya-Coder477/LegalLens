"""
pipeline/safety/hallucination_detector.py
=========================================
Hallucination Detection & Mitigation Engine for LegalLens Phase 7.
Identifies fabricated statutory sections, non-existent statutes, confabulated
penalties, version anachronisms, and unsupported legal extrapolations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pipeline.legal_ai.models import Claim
from pipeline.retrieval.models import RetrievedEvidence

from .citation_verifier import CitationVerifier
from .config import SafetyConfig, get_safety_config
from .models import (
    CitationVerificationResult,
    CitationVerificationStatus,
    ClaimVerificationResult,
    EntailmentStatus,
    HallucinationFlag,
    HallucinationType,
)


class HallucinationDetector:
    """
    Detects confabulated legal artifacts in AI responses.
    """

    def __init__(
        self,
        citation_verifier: Optional[CitationVerifier] = None,
        config: Optional[SafetyConfig] = None,
    ):
        self.config = config or get_safety_config()
        self.citation_verifier = citation_verifier or CitationVerifier(config=self.config)

    def scan_response(
        self,
        response_text: str,
        citations: List[CitationVerificationResult],
        claims: List[ClaimVerificationResult],
        evidence_map: Dict[str, RetrievedEvidence],
    ) -> List[HallucinationFlag]:
        """
        Run comprehensive multi-vector hallucination scan on generated content.
        """
        flags: List[HallucinationFlag] = []

        # 1. Check for Fabricated Citations / Sections
        for cit in citations:
            if cit.status == CitationVerificationStatus.FABRICATED:
                flags.append(
                    HallucinationFlag(
                        hallucination_type=HallucinationType.FABRICATED_SECTION,
                        flagged_text=cit.raw_citation,
                        severity="CRITICAL",
                        explanation=(
                            f"Cited legal provision '{cit.raw_citation}' does not exist in "
                            f"the statutory catalogue (document {cit.resolved_document_id})."
                        ),
                        mitigation_action="REDACT",
                    )
                )
            elif cit.status == CitationVerificationStatus.SUPERSEDED_VERSION:
                flags.append(
                    HallucinationFlag(
                        hallucination_type=HallucinationType.VERSION_ANACHRONISM,
                        flagged_text=cit.raw_citation,
                        severity="HIGH",
                        explanation=(
                            f"Cited provision '{cit.raw_citation}' references a superseded or amended version."
                        ),
                        mitigation_action="WARN",
                    )
                )

        # 2. Check for Contradictory Legal Assertions
        for clm in claims:
            if clm.status == EntailmentStatus.CONTRADICTED:
                flags.append(
                    HallucinationFlag(
                        hallucination_type=HallucinationType.CONTRADICTORY_ASSERTION,
                        flagged_text=clm.claim_text,
                        severity="CRITICAL",
                        explanation=clm.contradiction_notes or "Statement directly contradicts governing evidence.",
                        mitigation_action="REWRITE",
                    )
                )
            elif clm.status == EntailmentStatus.UNGROUNDED:
                flags.append(
                    HallucinationFlag(
                        hallucination_type=HallucinationType.UNSUPPORTED_EXTRAPOLATION,
                        flagged_text=clm.claim_text,
                        severity="HIGH",
                        explanation="Legal claim has no grounding in any retrieved statutory evidence.",
                        mitigation_action="WARN",
                    )
                )

        # 3. Check for Fabricated Penalties or Imprisonment Years
        penalty_flags = self._scan_fabricated_penalties(response_text, evidence_map)
        flags.extend(penalty_flags)

        return flags

    def _scan_fabricated_penalties(
        self,
        text: str,
        evidence_map: Dict[str, RetrievedEvidence],
    ) -> List[HallucinationFlag]:
        """
        Ensure specific monetary penalties or sentences in output exist in the cited evidence.
        """
        flags: List[HallucinationFlag] = []
        all_evidence_text = " ".join(ev.text for ev in evidence_map.values())

        # Match currency numbers like ₹50,000, Rs. 1,00,000, Rs 50000
        currency_pattern = r"(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{2})?)"
        found_amounts = re.findall(currency_pattern, text, re.IGNORECASE)

        for amt in found_amounts:
            clean_amt = amt.replace(",", "")
            if clean_amt not in all_evidence_text.replace(",", ""):
                flags.append(
                    HallucinationFlag(
                        hallucination_type=HallucinationType.FABRICATED_PENALTY,
                        flagged_text=f"₹{amt}",
                        severity="HIGH",
                        explanation=(
                            f"Monetary penalty amount ₹{amt} does not appear in any of the cited evidence chunks."
                        ),
                        mitigation_action="FLAG",
                    )
                )

        # Match imprisonment terms like "10 years imprisonment"
        prison_pattern = r"\b(\d+)\s*(?:years?|months?)\s*(?:imprisonment|rigorous imprisonment)\b"
        found_terms = re.finditer(prison_pattern, text, re.IGNORECASE)
        for m in found_terms:
            full_match = m.group(0)
            if full_match.lower() not in all_evidence_text.lower():
                flags.append(
                    HallucinationFlag(
                        hallucination_type=HallucinationType.FABRICATED_PENALTY,
                        flagged_text=full_match,
                        severity="CRITICAL",
                        explanation=f"Imprisonment penalty '{full_match}' is not found in the governing evidence.",
                        mitigation_action="REDACT",
                    )
                )

        return flags
