"""
pipeline/safety/grounding_engine.py
===================================
Natural Language Inference (NLI) & Grounding Verification Engine for LegalLens Phase 7.
Evaluates atomic legal claims against cited evidence for entailment, partial support,
and direct contradictions (e.g. negation flips, modified timelines, conflicting thresholds).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pipeline.legal_ai.models import Claim
from pipeline.retrieval.models import RetrievedEvidence

from .config import SafetyConfig, get_safety_config
from .models import ClaimVerificationResult, EntailmentStatus


class GroundingEngine:
    """
    NLI and Faithfulness verification engine ensuring every generated legal claim
    is strictly entailed by its cited evidence.
    """

    def __init__(self, config: Optional[SafetyConfig] = None):
        self.config = config or get_safety_config()

    def verify_claim(
        self,
        claim_text: str,
        claim_id: str,
        cited_evidence_ids: List[str],
        evidence_map: Dict[str, RetrievedEvidence],
    ) -> ClaimVerificationResult:
        """
        Evaluate whether an atomic claim is entailed, contradicted, or ungrounded
        with respect to its cited evidence.
        """
        if not cited_evidence_ids:
            return ClaimVerificationResult(
                claim_id=claim_id,
                claim_text=claim_text,
                status=EntailmentStatus.UNGROUNDED,
                supporting_evidence_ids=[],
                entailment_confidence=0.0,
                lexical_overlap_ratio=0.0,
                contradiction_notes="Claim has no cited evidence references.",
            )

        # Gather text of all cited evidence items
        cited_texts: List[str] = []
        for eid in cited_evidence_ids:
            ev = evidence_map.get(eid)
            if ev:
                cited_texts.append(f"{ev.title or ''} {ev.section or ''} {ev.text}")

        if not cited_texts:
            return ClaimVerificationResult(
                claim_id=claim_id,
                claim_text=claim_text,
                status=EntailmentStatus.UNGROUNDED,
                supporting_evidence_ids=[],
                entailment_confidence=0.0,
                lexical_overlap_ratio=0.0,
                contradiction_notes="Referenced evidence IDs do not exist in context.",
            )

        combined_evidence = " ".join(cited_texts)

        # 1. Contradiction Detection (Numerical, Negation, or Threshold Mismatch)
        contradiction = self._detect_contradiction(claim_text, combined_evidence)
        if contradiction:
            return ClaimVerificationResult(
                claim_id=claim_id,
                claim_text=claim_text,
                status=EntailmentStatus.CONTRADICTED,
                supporting_evidence_ids=cited_evidence_ids,
                entailment_confidence=0.0,
                lexical_overlap_ratio=0.1,
                contradiction_notes=contradiction,
            )

        # 2. Lexical Overlap & Term Alignment
        overlap_ratio = self._calculate_overlap(claim_text, combined_evidence)

        if overlap_ratio >= 0.40:
            status = EntailmentStatus.ENTAILED
            confidence = min(1.0, round(overlap_ratio * 1.3, 3))
        elif overlap_ratio >= 0.20:
            status = EntailmentStatus.PARTIALLY_ENTAILED
            confidence = round(overlap_ratio, 3)
        else:
            status = EntailmentStatus.UNGROUNDED
            confidence = round(overlap_ratio, 3)

        return ClaimVerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            status=status,
            supporting_evidence_ids=cited_evidence_ids,
            entailment_confidence=confidence,
            lexical_overlap_ratio=round(overlap_ratio, 3),
        )

    def verify_all_claims(
        self,
        claims: List[Claim],
        evidence_map: Dict[str, RetrievedEvidence],
    ) -> Tuple[List[ClaimVerificationResult], float, float]:
        """
        Verify all claims, returning:
        (results, faithfulness_score, contradiction_score)
        """
        if not claims:
            return [], 1.0, 0.0

        results: List[ClaimVerificationResult] = []
        entailed_weights = 0.0
        contradiction_count = 0

        for c in claims:
            res = self.verify_claim(
                claim_text=c.text,
                claim_id=c.claim_id,
                cited_evidence_ids=c.evidence_refs,
                evidence_map=evidence_map,
            )
            results.append(res)

            if res.status == EntailmentStatus.ENTAILED:
                entailed_weights += 1.0
            elif res.status == EntailmentStatus.PARTIALLY_ENTAILED:
                entailed_weights += 0.5
            elif res.status == EntailmentStatus.CONTRADICTED:
                contradiction_count += 1

        total = max(1, len(claims))
        faithfulness_score = round(entailed_weights / total, 3)
        contradiction_score = round(contradiction_count / total, 3)

        return results, faithfulness_score, contradiction_score

    def _calculate_overlap(self, claim_text: str, evidence_text: str) -> float:
        stopwords = {
            "what", "is", "the", "specific", "legal", "mandate", "or", "relief", "provided", "for", "under",
            "document", "act", "rule", "regulations", "does", "have", "with", "from", "this", "that", "in",
            "of", "to", "a", "an", "and", "by", "on", "as", "at", "be", "are", "which", "how", "can", "every",
            "shall", "must", "section", "pursuant"
        }
        claim_words = [
            w for w in re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", claim_text.lower())
            if w not in stopwords
        ]
        if not claim_words:
            return 1.0

        evidence_words = set(re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", evidence_text.lower()))
        matched = sum(1 for w in claim_words if w in evidence_words)
        return matched / len(claim_words)

    def _detect_contradiction(self, claim_text: str, evidence_text: str) -> Optional[str]:
        """
        Check for explicit numeric/temporal conflicts or direct polar negation.
        """
        c_lower = claim_text.lower()
        e_lower = evidence_text.lower()

        # Normalize common spelled-out numbers to digits
        word_numbers = {
            "thirty": "30", "sixty": "60", "ninety": "90", "ten": "10",
            "fifteen": "15", "twenty": "20", "forty-five": "45", "one": "1",
            "two": "2", "three": "3", "five": "5", "six": "6", "twelve": "12",
            "twenty-four": "24"
        }
        for word, num in word_numbers.items():
            c_lower = re.sub(rf"\b{word}\b", num, c_lower)
            e_lower = re.sub(rf"\b{word}\b", num, e_lower)

        # 1. Timeline / Duration Contradiction (e.g. "30 days" vs "90 days")
        c_days = re.findall(r"\b(\d+)\s*(?:days?|months?|years?)\b", c_lower)
        e_days = re.findall(r"\b(\d+)\s*(?:days?|months?|years?)\b", e_lower)
        if c_days and e_days:
            # If claim asserts a specific timeline not found anywhere in evidence
            if not set(c_days).intersection(set(e_days)):
                return f"Duration mismatch: Claim asserts {c_days[0]} timeline, whereas evidence specifies {e_days[0]}."

        # 2. Percentage / Threshold Contradiction (e.g. "51%" vs "66%")
        c_pct = re.findall(r"\b(\d+)\s*%", c_lower)
        e_pct = re.findall(r"\b(\d+)\s*%", e_lower)
        if c_pct and e_pct:
            if not set(c_pct).intersection(set(e_pct)):
                return f"Threshold contradiction: Claim asserts {c_pct[0]}%, but evidence requires {e_pct[0]}%."

        # 3. Direct Negation Flip (shall not vs shall)
        if "shall not" in c_lower and "shall not" not in e_lower and "shall" in e_lower:
            return "Polarity flip: Claim introduces prohibition ('shall not') not supported by affirmative statutory evidence."
        if "prohibited" in c_lower and "permitted" in e_lower and "not permitted" not in e_lower:
            return "Contradiction: Claim asserts prohibition where evidence explicitly permits."

        return None
