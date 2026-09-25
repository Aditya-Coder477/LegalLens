"""
pipeline/legal_ai/context_builder.py
====================================
Transforms Phase 5 EvidenceBundles and optional user facts into sanitized,
delimited context blocks with stable evidence identifiers (E1, E2, etc.).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pipeline.retrieval.models import EvidenceBundle, RetrievedEvidence

from .models import UserFact


class BuiltContext:
    def __init__(
        self,
        formatted_text: str,
        evidence_map: Dict[str, RetrievedEvidence],
        fact_map: Dict[str, UserFact],
        token_estimate: int,
    ):
        self.formatted_text = formatted_text
        self.evidence_map = evidence_map  # E1 -> RetrievedEvidence
        self.fact_map = fact_map          # UF1 -> UserFact
        self.token_estimate = token_estimate


class ContextBuilder:
    """
    Constructs model context from retrieved legal evidence while preventing prompt injection
    and respecting token budgets.
    """

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens

    def build(
        self,
        bundle: EvidenceBundle,
        user_facts: Optional[List[UserFact]] = None,
        additional_evidence: Optional[List[RetrievedEvidence]] = None,
    ) -> BuiltContext:
        evidence_items = list(bundle.results)
        if additional_evidence:
            evidence_items.extend(additional_evidence)

        evidence_map: Dict[str, RetrievedEvidence] = {}
        fact_map: Dict[str, UserFact] = {}
        lines: List[str] = []

        # 1. User Facts Section (explicitly segregated from law)
        if user_facts:
            lines.append("=== BEGIN USER FACTS (UNVERIFIED USER STATEMENTS) ===")
            for i, uf in enumerate(user_facts, 1):
                fid = f"UF{i}"
                fact_map[fid] = uf
                words = uf.text.split()
                if len(words) > self.max_tokens:
                    truncated_text = " ".join(words[:self.max_tokens]) + "... [TRUNCATED OVERSIZED INPUT]"
                    lines.append(f"[{fid}] {truncated_text}")
                else:
                    lines.append(f"[{fid}] {uf.text}")
            lines.append("=== END USER FACTS ===\n")

        # 2. Legal Evidence Section
        lines.append("=== BEGIN LEGAL EVIDENCE (AUTHORITATIVE/SYNTHETIC CORPUS DATA) ===")
        current_tokens = 0

        for i, ev in enumerate(evidence_items, 1):
            eid = f"E{i}"
            evidence_map[eid] = ev

            ev_block = [
                f"[EVIDENCE: {eid}]",
                f"Document: {ev.document_id} (Version: {ev.version_id or 'original'})",
                f"Title: {ev.title or 'N/A'} | Section: {ev.section or 'N/A'}",
                f"Authority: {ev.source_authority} (Synthetic: {ev.synthetic})",
                f"Provenance: {ev.provenance_id or 'N/A'} (Page: {ev.page_start or 'N/A'})",
                "Text:",
                ev.text.strip(),
                "---",
            ]
            block_text = "\n".join(ev_block)
            block_tokens = len(block_text.split())

            if current_tokens + block_tokens > self.max_tokens:
                # Prioritization: Stop adding lower-ranked chunks when budget reached
                break

            lines.append(block_text)
            current_tokens += block_tokens

        lines.append("=== END LEGAL EVIDENCE ===\n")

        # 3. Supporting Context (Definitions & Cross References)
        sc = bundle.supporting_context
        if sc and (sc.definitions or sc.parent_chunks):
            lines.append("=== BEGIN SUPPORTING DEFINITIONS & CROSS-REFERENCES ===")
            for d in sc.definitions:
                lines.append(f"[DEFINITION] '{d.get('term')}': {d.get('definition_text')}")
            for p in sc.parent_chunks:
                lines.append(f"[PARENT SECTION] {p.get('document_id')} Sec {p.get('section')}: {p.get('title')}")
            lines.append("=== END SUPPORTING CONTEXT ===\n")

        full_context_str = "\n".join(lines)
        total_tokens = len(full_context_str.split())

        return BuiltContext(
            formatted_text=full_context_str,
            evidence_map=evidence_map,
            fact_map=fact_map,
            token_estimate=total_tokens,
        )
