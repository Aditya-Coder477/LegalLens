"""
pipeline/legal_ai/validator.py
==============================
Evidence grounding validator and output schema verification for LegalLens Phase 6.
Ensures every claim is grounded, citations resolve to retrieved chunks,
and unsupported hallucinations are flagged or stripped.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pipeline.retrieval.models import RetrievedEvidence

from .config import LegalAIConfig, get_ai_config
from .context_builder import BuiltContext
from .models import Claim, ClaimType, LegalAIResponse, SupportStatus, TaskType


class ValidationResult:
    """Outcome of validating a LegalAIResponse against evidence context."""

    def __init__(
        self,
        is_valid: bool,
        claim_support_rate: float,
        resolved_evidence_refs: List[str],
        unresolved_evidence_refs: List[str],
        warnings: List[str],
        validated_response: LegalAIResponse,
    ):
        self.is_valid = is_valid
        self.claim_support_rate = claim_support_rate
        self.resolved_evidence_refs = resolved_evidence_refs
        self.unresolved_evidence_refs = unresolved_evidence_refs
        self.warnings = warnings
        self.validated_response = validated_response


class ResponseValidator:
    """
    Validates structured outputs produced by LLM providers against the
    retrieved EvidenceBundle context.
    """

    def __init__(self, config: Optional[LegalAIConfig] = None):
        self.config = config or get_ai_config()

    def validate_and_ground(
        self,
        raw_response: Dict[str, Any],
        task_type: TaskType,
        context: BuiltContext,
        evidence_items: Optional[List[RetrievedEvidence]] = None,
    ) -> LegalAIResponse:
        """
        Validate raw response dictionary, resolve citations, ground claims,
        and construct the canonical LegalAIResponse.
        """
        warnings: List[str] = []
        limitations: List[str] = raw_response.get("limitations", [])

        # 1. Check if evidence is available
        evidence_map = context.evidence_map
        valid_evidence_ids = set(evidence_map.keys())

        if not valid_evidence_ids:
            # No evidence context was provided or retrieved
            status = "NO_EVIDENCE"
            direct_answer = raw_response.get(
                "direct_answer",
                "The legal knowledge base does not contain evidence to address this query.",
            )
            warnings.append("No authoritative evidence found in the corpus for this request.")
            return LegalAIResponse(
                task_type=task_type,
                status=status,
                direct_answer=direct_answer,
                structured_data=raw_response,
                claims=[],
                evidence_refs=[],
                warnings=warnings,
                limitations=limitations,
                synthetic=True,
                data_status="SYNTHETIC_DEVELOPMENT_DATA",
                model=self.config.llm_model,
                provider=self.config.llm_provider,
                prompt_version="v1.0",
                claim_support_rate=1.0,
            )

        # 2. Extract and resolve evidence refs from raw response
        raw_refs: List[str] = []
        if "evidence_refs" in raw_response and isinstance(raw_response["evidence_refs"], list):
            raw_refs.extend(raw_response["evidence_refs"])

        # Also search for citation patterns like [E1], E1, [E2] in string fields
        text_content = str(raw_response)
        embedded_refs = re.findall(r"\b(E\d+)\b", text_content)
        all_candidate_refs = list(dict.fromkeys(raw_refs + embedded_refs))

        resolved_refs: List[str] = []
        unresolved_refs: List[str] = []

        for ref in all_candidate_refs:
            if ref in valid_evidence_ids:
                resolved_refs.append(ref)
            else:
                unresolved_refs.append(ref)

        if unresolved_refs:
            warnings.append(
                f"Response referenced ungrounded evidence IDs: {', '.join(unresolved_refs)}"
            )

        # 3. Process Claims and Grounding
        raw_claims = raw_response.get("claims", [])
        validated_claims: List[Claim] = []

        if raw_claims and isinstance(raw_claims, list):
            for c_data in raw_claims:
                if isinstance(c_data, dict):
                    c_text = c_data.get("text", "")
                    c_type_str = c_data.get("claim_type", "LEGAL_PROVISION")
                    try:
                        c_type = ClaimType(c_type_str)
                    except ValueError:
                        c_type = ClaimType.LEGAL_PROVISION

                    c_refs = [
                        r for r in c_data.get("evidence_refs", [])
                        if r in valid_evidence_ids
                    ]

                    # Grounding verification
                    if not c_refs:
                        # If no valid evidence refs, mark unsupported
                        support_status = SupportStatus.UNSUPPORTED
                        warnings.append(f"Claim unsupported by evidence: '{c_text[:50]}...'")
                    else:
                        # Verify that referenced evidence actually mentions key terms or supports it
                        is_supported = self._verify_claim_support(c_text, c_refs, evidence_map)
                        support_status = SupportStatus.SUPPORTED if is_supported else SupportStatus.PARTIALLY_SUPPORTED

                    validated_claims.append(
                        Claim(
                            text=c_text,
                            claim_type=c_type,
                            evidence_refs=c_refs,
                            support_status=support_status,
                        )
                    )
        elif "direct_answer" in raw_response and raw_response["direct_answer"]:
            # Auto-synthesize atomic claims if direct_answer provided without explicit claims
            ans_text = raw_response["direct_answer"]
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ans_text) if len(s.strip()) > 10]
            for s in sentences:
                s_refs = [r for r in resolved_refs if r in valid_evidence_ids]
                validated_claims.append(
                    Claim(
                        text=s,
                        claim_type=ClaimType.LEGAL_PROVISION,
                        evidence_refs=s_refs,
                        support_status=SupportStatus.SUPPORTED if s_refs else SupportStatus.UNSUPPORTED,
                    )
                )

        # 4. Calculate Claim Support Rate
        if validated_claims:
            supported_count = sum(
                1 for c in validated_claims
                if c.support_status in (SupportStatus.SUPPORTED, SupportStatus.PARTIALLY_SUPPORTED)
            )
            support_rate = round(supported_count / len(validated_claims), 3)
        else:
            support_rate = 1.0 if resolved_refs else 0.5

        # 5. Determine Response Status
        status = "SUCCESS"
        if not resolved_refs:
            status = "LOW_EVIDENCE"
            warnings.append("No specific evidence references were validated in this response.")
        elif support_rate < self.config.min_claim_support_rate:
            if self.config.grounding_mode == "strict":
                status = "LOW_EVIDENCE"
                warnings.append(
                    f"Claim support rate ({support_rate:.1%}) is below strict threshold "
                    f"({self.config.min_claim_support_rate:.1%})."
                )

        direct_answer = raw_response.get("direct_answer")
        if not direct_answer and "overview" in raw_response:
            direct_answer = raw_response["overview"]
        elif not direct_answer and "simplified_text" in raw_response:
            direct_answer = raw_response["simplified_text"]
        elif not direct_answer and "plain_language_meaning" in raw_response:
            direct_answer = raw_response["plain_language_meaning"]
        elif not direct_answer and "overall_summary" in raw_response:
            direct_answer = raw_response["overall_summary"]

        return LegalAIResponse(
            task_type=task_type,
            status=status,
            direct_answer=direct_answer,
            structured_data=raw_response,
            claims=validated_claims,
            evidence_refs=resolved_refs,
            warnings=warnings,
            limitations=limitations,
            synthetic=True,
            data_status="SYNTHETIC_DEVELOPMENT_DATA",
            model=self.config.llm_model,
            provider=self.config.llm_provider,
            prompt_version="v1.0",
            claim_support_rate=support_rate,
        )

    def _verify_claim_support(
        self,
        claim_text: str,
        evidence_refs: List[str],
        evidence_map: Dict[str, RetrievedEvidence],
    ) -> bool:
        """
        Check if the text of the claim is lexically grounded in the referenced evidence.
        """
        claim_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", claim_text.lower()))
        if not claim_words:
            return True

        evidence_words: Set[str] = set()
        for ref in evidence_refs:
            ev = evidence_map.get(ref)
            if ev:
                evidence_words.update(re.findall(r"\b[a-zA-Z]{4,}\b", ev.text.lower()))

        overlap = claim_words.intersection(evidence_words)
        # If at least 25% of significant claim words appear in the referenced evidence text
        overlap_ratio = len(overlap) / len(claim_words)
        return overlap_ratio >= 0.25
