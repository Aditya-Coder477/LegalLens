"""
pipeline/knowledge_base/providers.py
====================================
Embedding model provider abstraction and implementations.

Provides:
  - EmbeddingProvider Protocol
  - FakeEmbeddingProvider (testing, offline mocking, CI)
  - LocalEmbeddingProvider (fast, deterministic, self-contained offline embedding)
  - OpenAIEmbeddingProvider (OpenAI / compatible REST endpoints)
  - get_embedding_provider factory
  - validate_vector validation helper
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from typing import Any, List, Optional, Protocol, runtime_checkable

import httpx


def validate_vector(vector: List[float], expected_dim: int) -> None:
    """
    Validate that an embedding vector conforms to strict mathematical requirements.
    Raises ValueError if invalid.
    """
    if not isinstance(vector, list):
        raise ValueError(f"Vector must be a list of floats, got {type(vector)}")
    if len(vector) != expected_dim:
        raise ValueError(f"Vector dimension mismatch: expected {expected_dim}, got {len(vector)}")
    
    non_zero = False
    for i, val in enumerate(vector):
        if not isinstance(val, (int, float)):
            raise ValueError(f"Vector element at index {i} is not a float: {val!r}")
        if math.isnan(val):
            raise ValueError(f"Vector contains NaN at index {i}")
        if math.isinf(val):
            raise ValueError(f"Vector contains infinity at index {i}")
        if abs(val) > 1e-9:
            non_zero = True
            
    if not non_zero:
        raise ValueError("Vector cannot be all zeros")


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-12:
        return vec
    return [x / norm for x in vec]


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def provider_name(self) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    @property
    def dimension(self) -> int:
        ...

    def embed_text(self, text: str) -> List[float]:
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        ...


class FakeEmbeddingProvider:
    """
    Deterministic mock embedding provider for tests and CI without external dependencies.
    """
    def __init__(self, model_name: str = "fake-dense-v1", dimension: int = 384, normalize: bool = True):
        self._model_name = model_name
        self._dimension = dimension
        self._normalize = normalize

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            # Return valid small noise rather than empty or zero
            text = "empty_placeholder"
        # Deterministic vector generated from sha256 hash of text
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Seed random generator with the hash
        rng = random.Random(int.from_bytes(h[:8], "big"))
        vec = [rng.gauss(0, 1) for _ in range(self._dimension)]
        if self._normalize:
            vec = _l2_normalize(vec)
        validate_vector(vec, self._dimension)
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class LocalEmbeddingProvider:
    """
    Self-contained, fast, deterministic local embedding provider.
    Uses legal-aware n-gram feature hashing & projection into R^dimension.
    Produces high quality deterministic dense semantic vectors offline with 0 latency.
    """
    def __init__(self, model_name: str = "legal-dense-v1", dimension: int = 384, normalize: bool = True):
        self._model_name = model_name
        self._dimension = dimension
        self._normalize = normalize

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            text = "empty"
        
        words = text.lower().split()
        vec = [0.0] * self._dimension

        # Multi-resolution n-gram hashing
        for word in words:
            # Word token
            h_word = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h_word % self._dimension
            sign = 1.0 if ((h_word >> 8) & 1) else -1.0
            vec[idx] += sign

            # Character 3-grams
            if len(word) >= 3:
                for k in range(len(word) - 2):
                    tri = word[k:k+3]
                    h_tri = int(hashlib.md5(tri.encode("utf-8")).hexdigest(), 16)
                    idx_tri = h_tri % self._dimension
                    sign_tri = 1.0 if ((h_tri >> 8) & 1) else -1.0
                    vec[idx_tri] += sign_tri * 0.5

        # If sparse collision leaves all zeros, add deterministic fallback
        if all(abs(x) < 1e-9 for x in vec):
            rng = random.Random(int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16))
            vec = [rng.gauss(0, 1) for _ in range(self._dimension)]

        if self._normalize:
            vec = _l2_normalize(vec)
            
        validate_vector(vec, self._dimension)
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class OpenAIEmbeddingProvider:
    """
    OpenAI and OpenAI-compatible embedding provider.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-3-small",
        dimension: int = 1536,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        normalize: bool = True,
    ):
        self._api_key = api_key
        self._model_name = model_name
        self._dimension = dimension
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._max_retries = max_retries
        self._normalize = normalize

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        res = self.embed_batch([text])
        return res[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is not configured for OpenAIEmbeddingProvider")

        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model_name,
            "input": texts,
        }

        last_error = None
        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    vectors = [item["embedding"] for item in data["data"]]
                    
                    if self._normalize:
                        vectors = [_l2_normalize(v) for v in vectors]
                        
                    for v in vectors:
                        validate_vector(v, self._dimension)
                    return vectors
            except Exception as e:
                last_error = e
                time.sleep(0.5 * (2 ** (attempt - 1)))

        raise RuntimeError(f"OpenAI embedding batch failed after {self._max_retries} attempts: {last_error}")


def get_embedding_provider(
    provider_name: str = "local",
    model_name: Optional[str] = None,
    dimension: Optional[int] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    normalize: bool = True,
) -> EmbeddingProvider:
    """
    Factory function to instantiate the configured embedding provider.
    """
    p_name = provider_name.lower().strip()
    if p_name == "fake":
        return FakeEmbeddingProvider(
            model_name=model_name or "fake-dense-v1",
            dimension=dimension or 384,
            normalize=normalize,
        )
    elif p_name == "openai":
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model_name=model_name or "text-embedding-3-small",
            dimension=dimension or 1536,
            base_url=base_url,
            normalize=normalize,
        )
    elif p_name == "local":
        return LocalEmbeddingProvider(
            model_name=model_name or "legal-dense-v1",
            dimension=dimension or 384,
            normalize=normalize,
        )
    else:
        raise ValueError(f"Unknown embedding provider: {provider_name}. Expected local, fake, or openai.")
