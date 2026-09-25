"""
pipeline/knowledge_base/cache.py
================================
Persistent embedding cache for idempotency, cost reduction, and incremental ingestion.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class EmbeddingCacheManager:
    """
    Manages embedding caching on disk and in database.
    Cache key: (content_hash, provider, model, dimension)
    """

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, List[float]] = {}
        self._load()

    def _make_key(self, content_hash: str, provider: str, model: str, dimension: int) -> str:
        return f"{provider}:{model}:{dimension}:{content_hash}"

    def _load(self) -> None:
        if self.cache_file.exists():
            try:
                with self.cache_file.open("r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def save(self) -> None:
        temp_file = self.cache_file.with_suffix(".tmp")
        with temp_file.open("w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False)
        temp_file.replace(self.cache_file)

    def get(self, content_hash: str, provider: str, model: str, dimension: int) -> Optional[List[float]]:
        key = self._make_key(content_hash, provider, model, dimension)
        return self._cache.get(key)

    def put(self, content_hash: str, provider: str, model: str, dimension: int, vector: List[float]) -> None:
        key = self._make_key(content_hash, provider, model, dimension)
        self._cache[key] = vector

    def count(self) -> int:
        return len(self._cache)
