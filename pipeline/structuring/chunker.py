"""
pipeline/structuring/chunker.py
================================
Legal-aware hierarchical chunker.

Rules (from Phase 3 spec):
  - Target: 400–700 tokens, never exceeds 900 tokens (max)
  - Minimum: 100 tokens (merge small units upward if possible)
  - Preferred split boundary order:
      Section → Subsection → Clause → Paragraph → Sentence
  - Overlap: 50 tokens when a split is unavoidable
  - Never merge chunks from different versions
  - Never merge chunks across Section boundaries
  - embedding_text = "[{document_type}] {doc_title} | {chapter} | {section}: {heading}\\n\\n{text}"
  - retrieval_text = "{doc_id} Section {sec_num}. {heading}\\n{text}"

Inputs: LegalUnit objects
Outputs: ChunkRecord objects
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .models import ChunkRecord, ChunkType, LegalUnit
from . import MAX_TOKENS_DEFAULT, MIN_TOKENS_DEFAULT, OVERLAP_TOKENS_DEFAULT, TARGET_TOKENS_DEFAULT


# ──────────────────────────────────────────────
# Token helpers
# ──────────────────────────────────────────────

def _tok(text: str) -> int:
    """Simple whitespace token estimate."""
    return len(text.split()) if text else 0


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences using simple regex."""
    # Split on ". " followed by capital or end of numbered sub-item
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z("])', text)
    return [p.strip() for p in parts if p.strip()]


def _split_paragraphs(text: str) -> List[str]:
    """Split on double newlines or numbered sub-items."""
    parts = re.split(r'\n{2,}|\n(?=\(\d+\))', text)
    return [p.strip() for p in parts if p.strip()]


def _split_by_word_count(text: str, target_words: int) -> List[str]:
    """Hard-split by word count as a last resort (no natural boundaries)."""
    words = text.split()
    if len(words) <= target_words:
        return [text]
    parts = []
    for i in range(0, len(words), target_words):
        parts.append(" ".join(words[i : i + target_words]))
    return parts


def _overlap_prefix(text: str, overlap_tokens: int) -> str:
    """Return the last `overlap_tokens` words of text as a string."""
    words = text.split()
    if len(words) <= overlap_tokens:
        return text
    return " ".join(words[-overlap_tokens:])


# ──────────────────────────────────────────────
# Chunk ID generator
# ──────────────────────────────────────────────

_chunk_counters: Dict[str, int] = {}

def _reset_chunk_counters() -> None:
    _chunk_counters.clear()

def _next_chunk_id(doc_id: str, unit: LegalUnit, split_index: Optional[int] = None) -> str:
    """
    Generate a deterministic chunk_id.
    
    Format:
      Acts:      SYN-ACT-001-CH-01-S05  (or -2 for split)
      Rules:     SYN-RULE-004-R12
      Contracts: SYN-CONT-003-CLAUSE-14
      Judgments: SYN-JUDG-001-ISSUE-02
    """
    doc_type_prefix = _detect_prefix(doc_id)
    sec = unit.section_number or "0"

    if doc_type_prefix == "ACT" or doc_type_prefix == "AMEND":
        ch = unit.chapter_number or "X"
        ch_padded = ch.zfill(2) if ch.isdigit() else ch
        sec_padded = sec.zfill(2)
        base = f"{doc_id}-CH-{ch_padded}-S{sec_padded}"
    elif doc_type_prefix == "RULE":
        sec_padded = sec.zfill(2)
        base = f"{doc_id}-R{sec_padded}"
    elif doc_type_prefix == "CONT":
        base = f"{doc_id}-CLAUSE-{sec}"
    elif doc_type_prefix == "JUDG":
        chunk_name = _judgment_section_name(sec)
        base = f"{doc_id}-{chunk_name}-{sec.zfill(2)}"
    elif doc_type_prefix in ("NOTIF", "GUIDE", "CIRC"):
        base = f"{doc_id}-PARA-{sec.zfill(2)}"
    else:
        base = f"{doc_id}-UNIT-{sec}"

    if unit.subsection_number:
        base = f"{base}-SS{unit.subsection_number}"
    if split_index is not None:
        base = f"{base}-SPLIT{split_index}"

    return base


def _detect_prefix(doc_id: str) -> str:
    """Detect document class from doc_id."""
    if "ACT-010-v" in doc_id or "AMEND" in doc_id:
        return "AMEND"
    if "-ACT-" in doc_id:
        return "ACT"
    if "-RULE-" in doc_id:
        return "RULE"
    if "-CONT-" in doc_id:
        return "CONT"
    if "-JUDG-" in doc_id:
        return "JUDG"
    if "-NOTIF-" in doc_id:
        return "NOTIF"
    if "-GUIDE-" in doc_id:
        return "GUIDE"
    if "-CIRC-" in doc_id:
        return "CIRC"
    return "OTHER"


def _judgment_section_name(sec_num: str) -> str:
    names = {
        "1": "META", "2": "FACTS", "3": "ISSUE",
        "4": "ARG", "5": "REASON", "6": "ORDER",
    }
    return names.get(sec_num, "SEC")


# ──────────────────────────────────────────────
# Retrieval text builders
# ──────────────────────────────────────────────

def _build_embedding_text(unit: LegalUnit, doc_type: str) -> str:
    """
    Build embedding_text: context-enriched representation for semantic search.
    Format: [TYPE] {Title} | {Chapter} | {Section}: {Heading}
    
    {text}
    """
    parts = [f"[{doc_type.upper()}]"]
    
    if unit.document_title:
        parts.append(unit.document_title)
    
    chapter_str = ""
    if unit.chapter_number and unit.chapter_title:
        chapter_str = f"Chapter {unit.chapter_number}: {unit.chapter_title}"
    elif unit.chapter_title:
        chapter_str = unit.chapter_title
    
    if chapter_str:
        parts.append(chapter_str)

    section_str = ""
    if unit.section_number:
        heading = unit.heading or unit.section_title or ""
        section_str = f"Section {unit.section_number}"
        if heading:
            section_str += f": {heading}"
    
    if section_str:
        parts.append(section_str)

    header = " | ".join(parts)
    return f"{header}\n\n{unit.text}"


def _build_retrieval_text(unit: LegalUnit, doc_id: str) -> str:
    """
    Build retrieval_text: identifier-preserving format for BM25.
    Format: {doc_id} Section {sec_num}. {heading}
    {text}
    """
    sec = unit.section_number or ""
    heading = unit.heading or unit.section_title or ""
    
    if heading:
        header = f"{doc_id} Section {sec}. {heading}"
    else:
        header = f"{doc_id} Section {sec}"
    
    return f"{header}\n{unit.text}"


# ──────────────────────────────────────────────
# Main Chunker
# ──────────────────────────────────────────────

class LegalChunker:
    """
    Converts LegalUnit objects into ChunkRecord objects.

    Strategy:
    1. If unit is within target range [min, max] → produce 1 chunk
    2. If unit is too large → split at paragraph/sentence boundaries
    3. Small child subsections (<min) can be absorbed into their parent before chunking
    """

    def __init__(
        self,
        target_tokens: int = TARGET_TOKENS_DEFAULT,
        max_tokens: int = MAX_TOKENS_DEFAULT,
        min_tokens: int = MIN_TOKENS_DEFAULT,
        overlap_tokens: int = OVERLAP_TOKENS_DEFAULT,
    ):
        self.target_tokens  = target_tokens
        self.max_tokens     = max_tokens
        self.min_tokens     = min_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_unit(
        self,
        unit: LegalUnit,
        doc_type: str,
        existing_chunk_ids: Optional[set] = None,
    ) -> List[ChunkRecord]:
        """
        Convert one LegalUnit into one or more ChunkRecords.
        Never produces 0 records; always produces at least 1.
        """
        text   = unit.text.strip()
        tokens = _tok(text)
        
        if existing_chunk_ids is None:
            existing_chunk_ids = set()

        # Small unit — produce single chunk regardless
        if tokens <= self.max_tokens:
            return [self._make_chunk(unit, text, doc_type, existing_chunk_ids)]
        
        # Large unit — split
        return self._split_and_chunk(unit, text, doc_type, existing_chunk_ids)

    def _split_and_chunk(
        self,
        unit: LegalUnit,
        text: str,
        doc_type: str,
        existing_chunk_ids: set,
    ) -> List[ChunkRecord]:
        """Split large text at natural legal boundaries."""
        # Try paragraph splits first
        paragraphs = _split_paragraphs(text)
        if len(paragraphs) < 2:
            # Fall back to sentence splits
            paragraphs = _split_sentences(text)
        if len(paragraphs) < 2:
            # Final fallback: hard-split by word count
            paragraphs = _split_by_word_count(text, self.target_tokens)

        chunks: List[ChunkRecord] = []
        current_parts: List[str] = []
        current_tokens = 0
        overlap_text   = ""
        split_idx      = 0

        def flush(is_last: bool = False) -> None:
            nonlocal current_parts, current_tokens, overlap_text, split_idx
            if not current_parts:
                return
            fragment = " ".join(current_parts).strip()
            if overlap_text:
                fragment = overlap_text + " " + fragment
            
            sub_unit = LegalUnit(
                unit_id          = f"{unit.unit_id}-SPLIT{split_idx}",
                document_id      = unit.document_id,
                version_group_id = unit.version_group_id,
                version_id       = unit.version_id,
                unit_type        = unit.unit_type,
                chapter_number   = unit.chapter_number,
                chapter_title    = unit.chapter_title,
                section_number   = unit.section_number,
                section_title    = unit.section_title,
                subsection_number= unit.subsection_number,
                heading          = unit.heading,
                text             = fragment,
                page_start       = unit.page_start,
                page_end         = unit.page_end,
                legal_domain     = unit.legal_domain,
                document_title   = unit.document_title,
                act_year         = unit.act_year,
                jurisdiction     = unit.jurisdiction,
                parent_unit_id   = unit.unit_id,
                source_document_id = unit.source_document_id,
                source_sha256    = unit.source_sha256,
                provenance_id    = unit.provenance_id,
                local_file       = unit.local_file,
                synthetic        = True,
                source_authority = "SYNTHETIC",
            )
            
            chunk = self._make_chunk(
                sub_unit, fragment, doc_type, existing_chunk_ids,
                is_split=True, split_index=split_idx
            )
            chunks.append(chunk)
            split_idx += 1
            
            # Set overlap for next chunk
            overlap_text  = _overlap_prefix(fragment, self.overlap_tokens) if not is_last else ""
            current_parts = []
            current_tokens = 0

        for para in paragraphs:
            para_tokens = _tok(para)
            if current_tokens + para_tokens > self.target_tokens and current_parts:
                flush()
            current_parts.append(para)
            current_tokens += para_tokens

        if current_parts:
            flush(is_last=True)

        # Update total count
        total = len(chunks)
        for i, ch in enumerate(chunks):
            ch.split_total = total
            ch.split_index = i

        return chunks if chunks else [self._make_chunk(unit, text, doc_type, existing_chunk_ids)]

    def _make_chunk(
        self,
        unit: LegalUnit,
        text: str,
        doc_type: str,
        existing_chunk_ids: set,
        is_split: bool = False,
        split_index: Optional[int] = None,
    ) -> ChunkRecord:
        """Create a ChunkRecord from a LegalUnit."""
        chunk_id = _next_chunk_id(unit.document_id, unit, split_index)
        
        # Deduplicate chunk IDs within a run
        if chunk_id in existing_chunk_ids:
            counter = existing_chunk_ids.__len__()
            chunk_id = f"{chunk_id}-DUP{counter}"
        existing_chunk_ids.add(chunk_id)

        embedding_text  = _build_embedding_text(unit, doc_type)
        retrieval_text  = _build_retrieval_text(unit, unit.document_id)

        return ChunkRecord(
            chunk_id          = chunk_id,
            document_id       = unit.document_id,
            version_group_id  = unit.version_group_id,
            version_id        = unit.version_id,
            chunk_type        = unit.unit_type,
            title             = unit.section_title,
            chapter_number    = unit.chapter_number,
            chapter_title     = unit.chapter_title,
            section_number    = unit.section_number,
            section_title     = unit.section_title,
            subsection_number = unit.subsection_number,
            clause_number     = unit.clause_number,
            parent_unit_id    = unit.parent_unit_id,
            source_unit_id    = unit.unit_id,
            text              = text,
            embedding_text    = embedding_text,
            retrieval_text    = retrieval_text,
            page_start        = unit.page_start,
            page_end          = unit.page_end,
            token_count       = _tok(text),
            char_count        = len(text),
            word_count        = len(text.split()),
            synthetic         = True,
            source_authority  = "SYNTHETIC",
            source_document_id= unit.source_document_id,
            source_sha256     = unit.source_sha256,
            provenance_id     = unit.provenance_id,
            local_file        = unit.local_file,
            legal_domains     = [unit.legal_domain] if unit.legal_domain else [],
            is_split          = is_split,
            split_index       = split_index,
            split_total       = None,  # filled later if split
        )
