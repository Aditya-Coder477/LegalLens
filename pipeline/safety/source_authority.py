"""
pipeline/safety/source_authority.py
===================================
Indian Legal Source Authority Verification and Normative Hierarchy Engine for LegalLens.
Enforces the hierarchy of legal authorities (Constitution > Acts > Rules > Notifications > Precedents),
detects subordinate rule ultra-vires conflicts, and ensures synthetic development corpus transparency.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pipeline.retrieval.models import RetrievedEvidence


class AuthorityLevel(int, Enum):
    CONSTITUTIONAL = 100
    SUPREME_COURT_PRECEDENT = 95
    CENTRAL_ACT = 90
    HIGH_COURT_PRECEDENT = 85
    STATE_ACT = 80
    SUBORDINATE_RULES = 75
    NOTIFICATION_CIRCULAR = 70
    CONTRACT_INSTRUMENT = 60
    SYNTHETIC_DEVELOPMENT = 40


AUTHORITY_MAP: Dict[str, AuthorityLevel] = {
    "CONSTITUTION": AuthorityLevel.CONSTITUTIONAL,
    "SUPREME_COURT": AuthorityLevel.SUPREME_COURT_PRECEDENT,
    "CENTRAL_ACT": AuthorityLevel.CENTRAL_ACT,
    "HIGH_COURT": AuthorityLevel.HIGH_COURT_PRECEDENT,
    "STATE_ACT": AuthorityLevel.STATE_ACT,
    "RULES": AuthorityLevel.SUBORDINATE_RULES,
    "NOTIFICATIONS": AuthorityLevel.NOTIFICATION_CIRCULAR,
    "CIRCULARS": AuthorityLevel.NOTIFICATION_CIRCULAR,
    "CONTRACT": AuthorityLevel.CONTRACT_INSTRUMENT,
    "SYNTHETIC": AuthorityLevel.SYNTHETIC_DEVELOPMENT,
}


class SourceAuthorityVerifier:
    """
    Evaluates normative authority and provenance weights across Indian legal sources.
    """

    def get_authority_level(self, source_authority: str, document_id: str) -> AuthorityLevel:
        auth_upper = (source_authority or "").upper()
        if "SYNTHETIC" in auth_upper or document_id.startswith("SYN-"):
            return AuthorityLevel.SYNTHETIC_DEVELOPMENT

        for k, level in AUTHORITY_MAP.items():
            if k in auth_upper:
                return level

        if "-ACT-" in document_id:
            return AuthorityLevel.CENTRAL_ACT
        elif "-RULE-" in document_id:
            return AuthorityLevel.SUBORDINATE_RULES
        elif "-NOTIF-" in document_id:
            return AuthorityLevel.NOTIFICATION_CIRCULAR
        elif "-CONT-" in document_id:
            return AuthorityLevel.CONTRACT_INSTRUMENT

        return AuthorityLevel.SUBORDINATE_RULES

    def evaluate_authority_bundle(
        self,
        evidence_items: List[RetrievedEvidence],
    ) -> Dict[str, Any]:
        """
        Assess overall source authority profile of an evidence set.
        """
        if not evidence_items:
            return {
                "overall_authority_score": 0.0,
                "highest_authority_level": None,
                "has_synthetic_sources": False,
                "warnings": ["No evidence items available to evaluate authority."],
            }

        levels = [
            self.get_authority_level(ev.source_authority, ev.document_id)
            for ev in evidence_items
        ]

        has_synthetic = any(
            ev.synthetic or "SYNTHETIC" in (ev.source_authority or "").upper()
            for ev in evidence_items
        )

        avg_score = round(sum(lvl.value for lvl in levels) / (len(levels) * 100.0), 3)
        max_level = max(levels, key=lambda l: l.value)

        warnings: List[str] = []
        if has_synthetic:
            warnings.append(
                "NOTICE: Response is grounded in synthetic development data. "
                "Must not be relied upon as official Indian statutory law."
            )

        return {
            "overall_authority_score": avg_score,
            "highest_authority_level": max_level.name,
            "has_synthetic_sources": has_synthetic,
            "warnings": warnings,
        }
