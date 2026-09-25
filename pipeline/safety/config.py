"""
pipeline/safety/config.py
=========================
Configuration settings for Phase 7: Grounding, Citation Verification & Safety Guardrails.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env", override=False)


class SafetyConfig(BaseModel):
    # Verification & Grounding thresholds
    min_faithfulness_score: float = Field(
        default=float(os.getenv("MIN_FAITHFULNESS_SCORE", "0.80")),
        description="Minimum entailment/faithfulness ratio required for claims",
    )
    min_citation_precision: float = Field(
        default=float(os.getenv("MIN_CITATION_PRECISION", "0.75")),
        description="Minimum ratio of cited evidence items that must support claims",
    )
    max_hallucination_rate: float = Field(
        default=float(os.getenv("MAX_HALLUCINATION_RATE", "0.05")),
        description="Maximum permissible hallucination risk threshold",
    )

    # Safety & Guardrail flags
    strict_provenance_enforced: bool = Field(
        default=True,
        description="Require every citation to resolve to a stored KB chunk with SHA-256",
    )
    quarantine_injections: bool = Field(
        default=True,
        description="Neutralize and quarantine adversarial prompt injection payloads",
    )
    enforce_legal_disclaimers: bool = Field(
        default=True,
        description="Enforce mandatory statutory disclaimers on all outputs",
    )
    require_synthetic_watermark: bool = Field(
        default=True,
        description="Ensure synthetic datasets retain synthetic=True flags",
    )
    block_unauthorized_advice: bool = Field(
        default=True,
        description="Block or rewrite statements offering definitive legal guarantees",
    )

    # Storage paths
    safety_reports_dir: Path = Field(
        default=_PROJECT_ROOT / "legal-data" / "safety" / "reports",
        description="Directory for audit, citation, and grounding reports",
    )


@lru_cache(maxsize=1)
def get_safety_config() -> SafetyConfig:
    return SafetyConfig()
