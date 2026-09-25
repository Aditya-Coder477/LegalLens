"""
pipeline/legal_ai/config.py
===========================
Configuration settings for Phase 6: Legal Reasoning & AI Features.
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


class LegalAIConfig(BaseModel):
    # LLM Provider settings
    llm_provider: str = Field(
        default=os.getenv("LLM_PROVIDER", "local"),
        description="LLM provider name: local | mock | openai",
    )
    llm_model: str = Field(
        default=os.getenv("LLM_MODEL", "legal-reasoner-v1"),
        description="Model name/identifier",
    )
    llm_temperature: float = Field(
        default=float(os.getenv("LEGAL_LLM_TEMPERATURE", "0.0")),
        description="Sampling temperature (0.0 for deterministic factual responses)",
    )
    llm_max_output_tokens: int = Field(
        default=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048")),
        description="Max generation tokens",
    )
    llm_max_context_tokens: int = Field(
        default=int(os.getenv("LLM_MAX_CONTEXT_TOKENS", "4000")),
        description="Maximum input context budget tokens",
    )
    llm_timeout: float = Field(
        default=float(os.getenv("LLM_TIMEOUT", "30.0")),
        description="HTTP / API request timeout in seconds",
    )

    # Reasoning & Grounding safety settings
    grounding_mode: str = Field(
        default=os.getenv("LEGAL_AI_GROUNDING_MODE", "strict"),
        description="Grounding policy mode: strict | relaxed",
    )
    min_claim_support_rate: float = Field(
        default=float(os.getenv("MIN_CLAIM_SUPPORT_RATE", "0.8")),
        description="Minimum fraction of claims that must have valid evidence citations",
    )
    enforce_strict_grounding: bool = Field(
        default=True,
        description="Whether to downgrade or flag answers with insufficient claim grounding",
    )
    require_synthetic_marker: bool = Field(
        default=True,
        description="Ensure synthetic=True and source_authority=SYNTHETIC are maintained",
    )
    summary_default_length: str = Field(
        default=os.getenv("SUMMARY_DEFAULT_LENGTH", "MEDIUM"),
        description="Default summarization length: SHORT | MEDIUM | DETAILED",
    )

    # API keys & endpoints
    llm_api_key: Optional[str] = Field(
        default=os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", None)),
        description="API key for external LLM endpoints",
    )
    llm_base_url: Optional[str] = Field(
        default=os.getenv("LLM_BASE_URL", None),
        description="Base URL for OpenAI-compatible LLM endpoints",
    )

    # Output storage
    ai_reports_dir: Path = Field(
        default=_PROJECT_ROOT / "legal-data" / "ai" / "reports",
        description="Directory for AI evaluation & grounding reports",
    )

    @property
    def temperature(self) -> float:
        return self.llm_temperature

    @property
    def max_context_tokens(self) -> int:
        return self.llm_max_context_tokens


@lru_cache(maxsize=1)
def get_ai_config() -> LegalAIConfig:
    return LegalAIConfig()
