"""
pipeline/knowledge_base/config.py
==================================
Centralized Phase 4 Knowledge Base and Embedding configuration.
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


class KnowledgeBaseConfig(BaseModel):
    # Database settings
    database_url: str = Field(
        default=os.getenv(
            "DATABASE_URL",
            f"sqlite:///{_PROJECT_ROOT / 'legal-data' / 'knowledge_base' / 'knowledge_base.db'}"
        ),
        description="SQLAlchemy database URL (PostgreSQL + pgvector or SQLite fallback)",
    )
    database_url_test: Optional[str] = Field(
        default=os.getenv("DATABASE_URL_TEST", None),
        description="Test database URL",
    )

    # Embedding provider settings
    embedding_provider: str = Field(
        default=os.getenv("EMBEDDING_PROVIDER", "local"),
        description="Provider name: local | fake | openai",
    )
    embedding_model: str = Field(
        default=os.getenv("EMBEDDING_MODEL", "legal-dense-v1"),
        description="Model identifier",
    )
    embedding_dimension: int = Field(
        default=int(os.getenv("EMBEDDING_DIMENSION", "384")),
        description="Vector embedding dimension",
    )
    embedding_batch_size: int = Field(
        default=int(os.getenv("EMBEDDING_BATCH_SIZE", "64")),
        description="Batch size for embedding generation",
    )
    embedding_max_retries: int = Field(
        default=int(os.getenv("EMBEDDING_MAX_RETRIES", "3")),
        description="Maximum retries for failed embedding batches",
    )
    normalize_embeddings: bool = Field(
        default=os.getenv("NORMALIZE_EMBEDDINGS", "true").lower() in ("true", "1", "yes"),
        description="Whether to L2-normalize vectors",
    )
    vector_distance_metric: str = Field(
        default=os.getenv("VECTOR_DISTANCE_METRIC", "cosine"),
        description="Vector distance metric: cosine | l2 | inner_product",
    )

    # Storage paths
    kb_data_path: Path = Field(
        default=_PROJECT_ROOT / "legal-data" / "knowledge_base",
        description="Path to knowledge base root directory",
    )
    structured_chunks_path: Path = Field(
        default=_PROJECT_ROOT / "legal-data" / "synthetic" / "structured" / "chunks.jsonl",
        description="Path to Phase 3 structured chunks input",
    )

    # External APIs
    openai_api_key: Optional[str] = Field(
        default=os.getenv("OPENAI_API_KEY", None),
        description="Optional API key for OpenAI",
    )
    openai_base_url: Optional[str] = Field(
        default=os.getenv("OPENAI_BASE_URL", None),
        description="Optional base URL for OpenAI-compatible endpoint",
    )


@lru_cache(maxsize=1)
def get_kb_config() -> KnowledgeBaseConfig:
    return KnowledgeBaseConfig()
