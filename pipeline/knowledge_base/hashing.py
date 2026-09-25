"""
pipeline/knowledge_base/hashing.py
==================================
Deterministic content hashing and embedding hashing utilities using SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import struct
from typing import Any, Dict, List, Optional


def compute_content_hash(
    text: str,
    title: Optional[str] = None,
    document_id: Optional[str] = None,
    section_number: Optional[str] = None,
    embedding_text: Optional[str] = None,
) -> str:
    """
    Compute a deterministic 64-character hex SHA-256 hash of the canonical legal chunk content.
    If embedding_text is present, it forms the core of the representation, augmented
    by structural identifiers to guarantee consistency.
    """
    payload = {
        "text": text.strip(),
        "embedding_text": (embedding_text or "").strip(),
        "document_id": document_id or "",
        "section_number": section_number or "",
        "title": title or "",
    }
    canonical_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def compute_vector_hash(vector: List[float]) -> str:
    """
    Compute a deterministic SHA-256 hash for a float vector.
    Pack floats into binary IEEE 754 32-bit floats.
    """
    packed = struct.pack(f"{len(vector)}f", *vector)
    return hashlib.sha256(packed).hexdigest()
