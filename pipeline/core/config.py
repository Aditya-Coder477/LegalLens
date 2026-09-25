"""
pipeline/core/config.py
=======================
Loads config.yaml + .env and exposes a typed, validated PipelineConfig object.

Usage:
    from pipeline.core.config import get_config
    cfg = get_config()
    print(cfg.collection.request_delay_seconds)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


# Load .env file from project root (if it exists)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env", override=False)


# ──────────────────────────────────────────────
# Sub-models
# ──────────────────────────────────────────────

class CollectionConfig(BaseModel):
    request_delay_seconds: float = 2.5
    request_jitter_seconds: float = 1.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    timeout_seconds: float = 45.0
    max_concurrent_per_domain: int = 1
    user_agent: str = (
        "LegalLens-DataPipeline/1.0 "
        "(Research; India Legal AI Platform; contact: admin@legallens.in)"
    )
    # Tri-state policy when robots.txt cannot be fetched: "conservative" or "permissive"
    robots_unknown_policy: str = "permissive"


class SourceConfig(BaseModel):
    enabled: bool = True
    base_url: str = ""
    languages: list[str] = Field(default_factory=lambda: ["en"])
    index_paths: list[str] = Field(default_factory=list)
    source_authority: Optional[str] = None
    rate_limit_delay: Optional[float] = None
    max_concurrent: Optional[int] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    doc_types: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    disallowed_paths: list[str] = Field(default_factory=list)
    retry_attempts: Optional[int] = None


class IndiaCodeConfig(SourceConfig):
    base_url: str = "https://www.indiacode.nic.in"
    browse_rpp: int = 100
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    use_ecourtsindia_api: bool = True
    doc_types: list[str] = Field(
        default_factory=lambda: [
            "acts", "rules", "regulations", "notifications",
            "orders", "ordinances", "circulars"
        ]
    )
    allowed_paths: list[str] = Field(
        default_factory=lambda: ["/browse", "/handle", "/bitstream"]
    )
    disallowed_paths: list[str] = Field(
        default_factory=lambda: ["/discover", "/search-filter", "/login", "/register", "/statistics"]
    )


class IndiaCodeApiConfig(SourceConfig):
    base_url: str = "https://indiacode.ecourtsindia.com/api"
    enabled: bool = True
    source_authority: str = "SECONDARY_COMMUNITY"


class DataGovConfig(SourceConfig):
    base_url: str = "https://api.data.gov.in"
    daily_call_limit: int = 950
    topics: list[str] = Field(default_factory=list)


class EcourtsConfig(SourceConfig):
    enabled: bool = False
    manual_import_only: bool = True


class SupremeCourtConfig(SourceConfig):
    base_url: str = "https://www.sci.gov.in"
    static_docs_only: bool = True
    year_from: int = 2015
    year_to: Optional[int] = None
    allowed_paths: list[str] = Field(default_factory=lambda: ["/pdf/", "/wp-content/uploads/"])
    blocked_paths: list[str] = Field(default_factory=lambda: ["main.sci.gov.in", "scr.sci.gov.in"])
    index_paths: list[str] = Field(default_factory=lambda: ["/rules/"])


class SimpleSourceConfig(SourceConfig):
    pass


class SourcesConfig(BaseModel):
    india_code: IndiaCodeConfig = Field(default_factory=IndiaCodeConfig)
    india_code_api: IndiaCodeApiConfig = Field(default_factory=IndiaCodeApiConfig)
    data_gov: DataGovConfig = Field(default_factory=DataGovConfig)
    ecourts: EcourtsConfig = Field(default_factory=EcourtsConfig)
    supreme_court: SupremeCourtConfig = Field(default_factory=SupremeCourtConfig)
    nalsa: SimpleSourceConfig = Field(
        default_factory=lambda: SimpleSourceConfig(
            base_url="https://nalsa.gov.in",
            index_paths=["/notifications/", "/statistics/"]
        )
    )
    legislative_dept: SimpleSourceConfig = Field(
        default_factory=lambda: SimpleSourceConfig(
            base_url="https://legislative.gov.in",
            index_paths=["/constitution-of-india/", "/central-acts/", "/ordinances/", "/amendment-acts/"]
        )
    )
    meity: SimpleSourceConfig = Field(
        default_factory=lambda: SimpleSourceConfig(
            base_url="https://www.meity.gov.in",
            index_paths=["/content/acts-rules", "/content/notifications"]
        )
    )


class OcrConfig(BaseModel):
    mode: str = "inline"           # "inline" | "offline"
    min_chars_per_page: int = 100
    tesseract_lang: str = "eng"
    dpi: int = 300


class ClassificationConfig(BaseModel):
    keyword_classifier_enabled: bool = True
    llm_classifier_enabled: bool = False
    llm_confidence_threshold: float = 0.55
    min_confidence: float = 0.25


class DedupConfig(BaseModel):
    url_dedup: bool = True
    sha256_dedup: bool = True
    title_year_dedup: bool = True
    similarity_threshold: float = 0.92


class StorageConfig(BaseModel):
    raw_dir: str = "legal-data/raw"
    processed_dir: str = "legal-data/processed"
    datasets_dir: str = "legal-data/datasets"
    logs_dir: str = "legal-data/logs"
    evaluation_dir: str = "legal-data/evaluation"


# ──────────────────────────────────────────────
# Top-level config
# ──────────────────────────────────────────────

class PipelineConfig(BaseModel):
    collection: CollectionConfig = Field(default_factory=CollectionConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    dedup: DedupConfig = Field(default_factory=DedupConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # Secrets (read from env, never from YAML)
    data_gov_api_key: Optional[str] = Field(default=None)
    llm_provider: Optional[str] = Field(default=None)
    llm_api_key: Optional[str] = Field(default=None)
    llm_model: Optional[str] = Field(default=None)

    @field_validator("data_gov_api_key", mode="before")
    @classmethod
    def load_data_gov_key(cls, v):
        return v or os.environ.get("DATA_GOV_API_KEY")

    @field_validator("llm_provider", mode="before")
    @classmethod
    def load_llm_provider(cls, v):
        return v or os.environ.get("LLM_PROVIDER")

    @field_validator("llm_api_key", mode="before")
    @classmethod
    def load_llm_key(cls, v):
        return v or os.environ.get("LLM_API_KEY")

    @field_validator("llm_model", mode="before")
    @classmethod
    def load_llm_model(cls, v):
        return v or os.environ.get("LLM_MODEL")

    # ----------------------------------------------------------
    # URL overrides from environment (for testing / local dev)
    # ----------------------------------------------------------
    @property
    def india_code_base_url(self) -> str:
        return os.environ.get("INDIA_CODE_BASE_URL", self.sources.india_code.base_url)

    @property
    def india_code_api_base(self) -> str:
        return os.environ.get("INDIA_CODE_API_BASE", self.sources.india_code_api.base_url)

    @property
    def data_gov_api_base(self) -> str:
        return os.environ.get("DATA_GOV_API_BASE", self.sources.data_gov.base_url)

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT


# ──────────────────────────────────────────────
# Loader (cached singleton)
# ──────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_config(config_path: Optional[str] = None) -> PipelineConfig:
    """
    Load and validate PipelineConfig from config.yaml + environment variables.

    Args:
        config_path: Override config file path (default: project_root/config.yaml).

    Returns:
        Validated PipelineConfig instance (cached after first call).
    """
    path = Path(config_path) if config_path else _PROJECT_ROOT / "config.yaml"
    if not path.exists():
        return PipelineConfig()

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return PipelineConfig.model_validate(raw)


def reload_config(config_path: Optional[str] = None) -> PipelineConfig:
    """Force reload config (clears LRU cache)."""
    get_config.cache_clear()
    return get_config(config_path)
