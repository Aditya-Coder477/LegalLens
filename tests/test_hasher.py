"""
tests/test_hasher.py
=====================
Tests for pipeline.core.hasher
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from pipeline.core.hasher import (
    is_duplicate_by_hash,
    sha256_bytes,
    sha256_file,
    sha256_text,
    verify_file_hash,
)


def _make_file(content: bytes) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


class TestSha256File:
    def test_correct_hash(self):
        content = b"Hello, Indian Legal System!"
        expected = hashlib.sha256(content).hexdigest()
        path = _make_file(content)
        try:
            assert sha256_file(path) == expected
        finally:
            path.unlink()

    def test_empty_file(self):
        path = _make_file(b"")
        try:
            result = sha256_file(path)
            assert len(result) == 64
            assert result == hashlib.sha256(b"").hexdigest()
        finally:
            path.unlink()

    def test_large_file(self):
        content = b"x" * (5 * 1024 * 1024)  # 5 MB
        expected = hashlib.sha256(content).hexdigest()
        path = _make_file(content)
        try:
            assert sha256_file(path) == expected
        finally:
            path.unlink()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            sha256_file(Path("/nonexistent/file.pdf"))

    def test_returns_64_hex_chars(self):
        path = _make_file(b"test")
        try:
            result = sha256_file(path)
            assert len(result) == 64
            assert all(c in "0123456789abcdef" for c in result)
        finally:
            path.unlink()


class TestSha256Text:
    def test_known_hash(self):
        text = "Indian Contract Act, 1872"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert sha256_text(text) == expected

    def test_empty_string(self):
        result = sha256_text("")
        assert len(result) == 64


class TestSha256Bytes:
    def test_bytes(self):
        data = b"\x00\x01\x02"
        assert sha256_bytes(data) == hashlib.sha256(data).hexdigest()


class TestVerifyFileHash:
    def test_match(self):
        content = b"test content"
        path = _make_file(content)
        correct_hash = hashlib.sha256(content).hexdigest()
        try:
            assert verify_file_hash(path, correct_hash) is True
        finally:
            path.unlink()

    def test_mismatch(self):
        content = b"test content"
        path = _make_file(content)
        wrong_hash = "a" * 64
        try:
            assert verify_file_hash(path, wrong_hash) is False
        finally:
            path.unlink()

    def test_case_insensitive(self):
        content = b"abc"
        path = _make_file(content)
        h = hashlib.sha256(content).hexdigest().upper()
        try:
            assert verify_file_hash(path, h) is True
        finally:
            path.unlink()


class TestIsDuplicate:
    def test_known_hash(self):
        sha = "a" * 64
        known = {"a" * 64, "b" * 64}
        assert is_duplicate_by_hash(sha, known) is True

    def test_unknown_hash(self):
        sha = "c" * 64
        known = {"a" * 64, "b" * 64}
        assert is_duplicate_by_hash(sha, known) is False

    def test_case_insensitive(self):
        sha_lower = "abcdef" * 10 + "abcd"
        sha_upper = sha_lower.upper()
        known = {sha_upper}
        assert is_duplicate_by_hash(sha_lower, known) is True
