"""
pipeline/safety
===============
Phase 7: Grounding, Citation Verification, Hallucination Detection & Safety Guardrails
for LegalLens.
"""

from .config import SafetyConfig, get_safety_config
from .models import (
    CitationVerificationResult,
    CitationVerificationStatus,
    ClaimVerificationResult,
    EntailmentStatus,
    HallucinationFlag,
    HallucinationType,
    SafetyAuditResult,
    SafetyViolationType,
)
from .service import SafetyService

__version__ = "1.0.0"
__all__ = [
    "SafetyConfig",
    "get_safety_config",
    "CitationVerificationResult",
    "CitationVerificationStatus",
    "ClaimVerificationResult",
    "EntailmentStatus",
    "HallucinationFlag",
    "HallucinationType",
    "SafetyAuditResult",
    "SafetyViolationType",
    "SafetyService",
]
