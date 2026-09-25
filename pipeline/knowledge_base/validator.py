"""
pipeline/knowledge_base/validator.py
====================================
Comprehensive validators for Phase 4:
  1. Input Validator (checks Phase 3 chunks.jsonl before ingestion)
  2. Knowledge Base Validator (checks canonical KB records, database, provenance, and vector embeddings)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .db import DatabaseManager
from .db_models import EmbeddingTable, KBChunkTable
from .hashing import compute_content_hash
from .providers import validate_vector


class KBValidationIssue:
    def __init__(self, category: str, rule: str, severity: str, message: str):
        self.category = category
        self.rule = rule
        self.severity = severity  # CRITICAL, WARNING, INFO
        self.message = message

    def to_dict(self) -> Dict[str, str]:
        return {
            "category": self.category,
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
        }

    def __str__(self) -> str:
        return f"[{self.severity}][{self.category}] {self.rule}: {self.message}"


class InputChunkValidator:
    """
    Validates Phase 3 chunks.jsonl prior to knowledge base ingestion.
    """

    def __init__(self, chunks_path: Path):
        self.chunks_path = chunks_path

    def validate(self) -> Tuple[bool, List[KBValidationIssue], Dict[str, Any]]:
        issues: List[KBValidationIssue] = []
        stats: Dict[str, Any] = {"total_records": 0, "valid_records": 0}

        if not self.chunks_path.exists():
            issues.append(
                KBValidationIssue("file", "exists", "CRITICAL", f"Input file not found: {self.chunks_path}")
            )
            return False, issues, stats

        seen_chunk_ids: Set[str] = set()

        with self.chunks_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                stats["total_records"] += 1

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    issues.append(
                        KBValidationIssue("syntax", "json_valid", "CRITICAL", f"Line {line_no}: Malformed JSON: {e}")
                    )
                    continue

                # 1. Identity checks
                chunk_id = record.get("chunk_id")
                if not chunk_id:
                    issues.append(
                        KBValidationIssue("identity", "chunk_id_required", "CRITICAL", f"Line {line_no}: Missing chunk_id")
                    )
                elif chunk_id in seen_chunk_ids:
                    issues.append(
                        KBValidationIssue("identity", "chunk_id_unique", "CRITICAL", f"Line {line_no}: Duplicate chunk_id: {chunk_id}")
                    )
                else:
                    seen_chunk_ids.add(chunk_id)

                if not record.get("document_id"):
                    issues.append(
                        KBValidationIssue("identity", "document_id_required", "CRITICAL", f"Line {line_no}: Missing document_id")
                    )

                # 2. Content checks
                text = record.get("text", "")
                if not text or not text.strip():
                    issues.append(
                        KBValidationIssue("content", "text_non_empty", "CRITICAL", f"Line {line_no} ({chunk_id}): Empty text")
                    )

                emb_text = record.get("embedding_text", "")
                if not emb_text or not emb_text.strip():
                    issues.append(
                        KBValidationIssue("content", "embedding_text_non_empty", "CRITICAL", f"Line {line_no} ({chunk_id}): Missing embedding_text")
                    )

                # 3. Provenance and Synthetic Guardrails
                if not record.get("synthetic"):
                    issues.append(
                        KBValidationIssue("safety", "synthetic_flag", "CRITICAL", f"Line {line_no} ({chunk_id}): synthetic must be True")
                    )

                if record.get("source_authority") != "SYNTHETIC":
                    issues.append(
                        KBValidationIssue("safety", "source_authority", "CRITICAL", f"Line {line_no} ({chunk_id}): source_authority must be 'SYNTHETIC'")
                    )

                stats["valid_records"] += 1

        is_valid = not any(iss.severity == "CRITICAL" for iss in issues)
        return is_valid, issues, stats


class KnowledgeBaseValidator:
    """
    Validates canonical KB records, vector embeddings, provenance, and database integrity.
    """

    def __init__(self, db_manager: DatabaseManager, expected_dimension: int = 384):
        self.db = db_manager
        self.expected_dimension = expected_dimension

    def validate(self) -> Tuple[bool, List[KBValidationIssue], Dict[str, Any]]:
        issues: List[KBValidationIssue] = []
        stats: Dict[str, Any] = {
            "total_chunks": 0,
            "total_embeddings": 0,
            "embedded_chunks": 0,
            "orphan_chunks": 0,
            "orphan_embeddings": 0,
        }

        with self.db.session_scope() as session:
            chunks = session.query(KBChunkTable).all()
            embeddings = session.query(EmbeddingTable).all()

            stats["total_chunks"] = len(chunks)
            stats["total_embeddings"] = len(embeddings)

            if len(chunks) == 0:
                issues.append(
                    KBValidationIssue("database", "chunks_not_empty", "CRITICAL", "Knowledge Base has 0 chunks")
                )
                return False, issues, stats

            chunk_map = {c.kb_chunk_id: c for c in chunks}
            emb_by_kb_id: Dict[str, List[EmbeddingTable]] = {}
            for e in embeddings:
                emb_by_kb_id.setdefault(e.kb_chunk_id, []).append(e)

            # 1. Identity & Content & Provenance Validation
            seen_kb_chunk_ids: Set[str] = set()
            for c in chunks:
                if c.kb_chunk_id in seen_kb_chunk_ids:
                    issues.append(
                        KBValidationIssue("identity", "kb_chunk_id_unique", "CRITICAL", f"Duplicate kb_chunk_id: {c.kb_chunk_id}")
                    )
                seen_kb_chunk_ids.add(c.kb_chunk_id)

                if not c.text or not c.text.strip():
                    issues.append(
                        KBValidationIssue("content", "text_not_empty", "CRITICAL", f"Chunk {c.chunk_id} has empty text")
                    )

                if not c.embedding_text or not c.embedding_text.strip():
                    issues.append(
                        KBValidationIssue("content", "embedding_text_not_empty", "CRITICAL", f"Chunk {c.chunk_id} has empty embedding_text")
                    )

                # Content hash check
                expected_hash = compute_content_hash(
                    text=c.text,
                    title=c.title,
                    document_id=c.document_id,
                    section_number=c.section,
                    embedding_text=c.embedding_text,
                )
                if c.content_hash != expected_hash:
                    issues.append(
                        KBValidationIssue("content", "content_hash_integrity", "WARNING", f"Chunk {c.chunk_id} content_hash mismatch")
                    )

                # Provenance
                if not c.synthetic:
                    issues.append(
                        KBValidationIssue("provenance", "synthetic_flag", "CRITICAL", f"Chunk {c.chunk_id} synthetic is not True")
                    )
                if c.source_authority != "SYNTHETIC":
                    issues.append(
                        KBValidationIssue("provenance", "source_authority", "CRITICAL", f"Chunk {c.chunk_id} source_authority is not 'SYNTHETIC'")
                    )
                if not c.source_sha256 or len(c.source_sha256) != 64:
                    issues.append(
                        KBValidationIssue("provenance", "source_sha256", "WARNING", f"Chunk {c.chunk_id} missing valid source_sha256")
                    )

            # 2. Embedding Validation
            for e in embeddings:
                if e.kb_chunk_id not in chunk_map:
                    stats["orphan_embeddings"] += 1
                    issues.append(
                        KBValidationIssue("database", "orphan_embedding", "CRITICAL", f"Embedding references non-existent kb_chunk_id {e.kb_chunk_id}")
                    )

                # Vector dimension and values check
                try:
                    vec = json.loads(e.vector)
                    validate_vector(vec, self.expected_dimension)
                except Exception as err:
                    issues.append(
                        KBValidationIssue("embedding", "vector_math_valid", "CRITICAL", f"Invalid vector for kb_chunk_id {e.kb_chunk_id}: {err}")
                    )

            # 3. Embedding Coverage
            embedded_count = sum(1 for c in chunks if c.kb_chunk_id in emb_by_kb_id)
            stats["embedded_chunks"] = embedded_count
            if embedded_count < len(chunks):
                missing = len(chunks) - embedded_count
                issues.append(
                    KBValidationIssue("embedding", "embedding_coverage", "WARNING", f"{missing} chunks are missing embeddings")
                )

        critical_count = sum(1 for iss in issues if iss.severity == "CRITICAL")
        return (critical_count == 0), issues, stats
