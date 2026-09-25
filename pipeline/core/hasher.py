"""
pipeline/core/hasher.py
=======================
SHA-256 hashing utilities for raw file integrity and deduplication.

Rules:
- Always hash the ORIGINAL raw file (not a processed copy)
- Streaming reads: memory-safe for very large PDFs
- Never silently swallow errors
"""

from __future__ import annotations

import hashlib
from pathlib import Path


CHUNK_SIZE = 1024 * 1024  # 1 MB chunks for streaming hash


def sha256_file(path: str | Path) -> str:
    """
    Compute the SHA-256 hex digest of a file using streaming reads.
    Memory-safe: reads in 1 MB chunks regardless of file size.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        64-character lowercase hex string.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
        OSError: On other I/O errors.
    """
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 of a bytes object."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str, encoding: str = "utf-8") -> str:
    """Compute SHA-256 of a text string."""
    return hashlib.sha256(text.encode(encoding)).hexdigest()


def verify_file_hash(path: str | Path, expected_sha256: str) -> bool:
    """
    Verify that a file's SHA-256 matches the expected digest.

    Returns:
        True if the file hash matches expected_sha256, False otherwise.
    """
    actual = sha256_file(path)
    return actual.lower() == expected_sha256.lower()


def is_duplicate_by_hash(sha256: str, known_hashes: set[str]) -> bool:
    """
    Check if a SHA-256 hash already exists in the known-hashes set.

    Args:
        sha256: 64-char hex digest to check.
        known_hashes: Set of previously seen SHA-256 digests (from catalogue).

    Returns:
        True if this hash is already known (duplicate).
    """
    target = sha256.lower()
    return any(target == h.lower() for h in known_hashes)
