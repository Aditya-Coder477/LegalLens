"""
pipeline/structuring/parser.py
===============================
Legal structure parser: converts existing sections.jsonl records + raw text
into normalized LegalUnit records, per document type.

Architecture:
  - Uses existing sections.jsonl as the primary structural source
    (all structural parsing was already done in Phase 2)
  - Uses raw .txt files for:
      * subsection detection (numbered paragraphs "(1)", "(2)", "(a)", "(b)")
      * definition extraction
      * cross-reference detection
  - Deterministic, regex-based — no LLMs

Supported document types:
  act, amendment, rule, regulation, notification, circular,
  guideline, judgment, contract
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

from .models import ChunkType, JUDGMENT_SECTION_MAP, LegalUnit


# ──────────────────────────────────────────────
# Regex Patterns
# ──────────────────────────────────────────────

# Subsection patterns: (1), (2), (3)
RE_NUMBERED_SUBSECTION = re.compile(r"^\((\d+)\)\s+(.+?)(?=\n\(\d+\)|\Z)", re.MULTILINE | re.DOTALL)

# Clause patterns: (a), (b), (c)
RE_LETTERED_CLAUSE = re.compile(r"^\(([a-z])\)\s+(.+?)(?=\n\([a-z]\)|\Z)", re.MULTILINE | re.DOTALL)

# Cross-reference patterns
RE_CROSSREF_SECTION  = re.compile(r"\bSection\s+(\d+[A-Z]?)(?:\((\d+)\))?(?:\(([a-z])\))?")
RE_CROSSREF_RULE     = re.compile(r"\bRule\s+(\d+[A-Z]?)(?:\((\d+)\))?")
RE_CROSSREF_ARTICLE  = re.compile(r"\bArticle\s+(\d+[A-Z]?)(?:\((\d+)\))?")
RE_CROSSREF_ACT      = re.compile(r"\bSYN-ACT-(\d{3})\b")
RE_CROSSREF_CLAUSE   = re.compile(r"\bClause\s+(\d+[A-Z]?)(?:\((\d+)\))?")

# Definition patterns
RE_DEFINITION_QUOTED  = re.compile(r'"([^"]{2,80})"\s+means\s+(.{10,400}?)(?:\.|;)', re.DOTALL)
RE_DEFINITION_SINGLE  = re.compile(r"'([^']{2,80})'\s+means\s+(.{10,400}?)(?:\.|;)", re.DOTALL)
RE_DEFINITION_DASH    = re.compile(r'"([^"]{2,80})"\s+—\s*(.{10,400}?)(?:\.|;)', re.DOTALL)

# For preamble detection
RE_PREAMBLE = re.compile(r"##\s+PREAMBLE\s*\n(.+?)(?=\n##|\Z)", re.DOTALL)


# ──────────────────────────────────────────────
# Document-type → ChunkType mapping
# ──────────────────────────────────────────────

DOC_TYPE_TO_SECTION_CHUNK_TYPE: Dict[str, ChunkType] = {
    "act":          ChunkType.SECTION,
    "amendment":    ChunkType.SECTION,
    "rule":         ChunkType.RULE,
    "regulation":   ChunkType.REGULATION,
    "notification": ChunkType.NOTIFICATION_PARA,
    "circular":     ChunkType.NOTIFICATION_PARA,
    "guideline":    ChunkType.GUIDANCE_SECTION,
    "judgment":     ChunkType.JUDGMENT_FACTS,     # overridden per section
    "contract":     ChunkType.CONTRACT_CLAUSE,
}


# ──────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────

def _count_tokens(text: str) -> int:
    """Simple whitespace-based token estimate (no LLM required)."""
    return len(text.split())


def _make_unit_id(document_id: str, section_number: str, sub_idx: Optional[int] = None) -> str:
    """Generate a deterministic unit_id."""
    base = f"{document_id}-UNIT-SEC{section_number}"
    if sub_idx is not None:
        base += f"-SS{sub_idx}"
    return base


def _detect_chunk_type(doc_type: str, section_number: str) -> ChunkType:
    """Detect the appropriate ChunkType for a section, considering doc-type and number."""
    if doc_type == "judgment":
        return JUDGMENT_SECTION_MAP.get(section_number, ChunkType.JUDGMENT_REASONING)
    return DOC_TYPE_TO_SECTION_CHUNK_TYPE.get(doc_type, ChunkType.SECTION)


# ──────────────────────────────────────────────
# Main Parser
# ──────────────────────────────────────────────

class LegalStructureParser:
    """
    Converts sections.jsonl records into LegalUnit objects.
    
    Input:  One section dict (from sections.jsonl) + document dict
    Output: One or more LegalUnit objects (unit + child subsections/clauses)
    """

    def __init__(self, raw_data_root: Path):
        self.raw_data_root = raw_data_root

    def parse_section(
        self,
        section: dict,
        document: dict,
        provenance_map: Dict[str, dict],
        existing_units: Dict[str, str],  # section_id → unit_id (for parent linking)
    ) -> List[LegalUnit]:
        """
        Parse one section dict into a list of LegalUnit objects.
        
        The primary unit is created from the section record.
        Sub-units are created from numbered/lettered subsections within the text
        only if the section text is long enough to warrant splitting.
        
        Returns: [primary_unit, *sub_units]
        """
        doc_id   = document["document_id"]
        doc_type = document.get("document_type", "other")
        sec_num  = section.get("section_number", "0")
        
        # Build provenance linkage
        prov = provenance_map.get(doc_id, {})
        
        # Infer chapter info
        chapter_raw = section.get("chapter", None)
        chapter_num, chapter_title = self._parse_chapter(chapter_raw)

        # Build primary unit
        chunk_type = _detect_chunk_type(doc_type, sec_num)
        
        primary = LegalUnit(
            unit_id             = _make_unit_id(doc_id, sec_num),
            document_id         = doc_id,
            version_group_id    = section.get("version_group_id") or document.get("document_version_group_id"),
            version_id          = section.get("version_id") or document.get("version_label"),
            unit_type           = chunk_type,
            chapter_number      = chapter_num,
            chapter_title       = chapter_title,
            section_number      = sec_num,
            section_title       = section.get("heading") or section.get("title"),
            heading             = section.get("heading") or section.get("title"),
            text                = section.get("text", ""),
            provisions          = section.get("provisions", []),
            explanations        = section.get("explanations", []),
            page_start          = section.get("page_start"),
            page_end            = section.get("page_end"),
            legal_domain        = section.get("domain") or document.get("legal_domain"),
            document_title      = document.get("title"),
            act_year            = document.get("act_year"),
            jurisdiction        = document.get("jurisdiction"),
            source_document_id  = doc_id,
            source_sha256       = document.get("sha256"),
            provenance_id       = prov.get("provenance_id"),
            local_file          = prov.get("local_file"),
            synthetic           = True,
            source_authority    = "SYNTHETIC",
            estimated_tokens    = _count_tokens(section.get("text", "")),
        )
        
        units = [primary]

        # Parse subsections only for acts/amendments/rules (legislation) 
        # where text uses (1), (2), ... numbering
        if doc_type in ("act", "amendment", "rule", "regulation"):
            sub_units = self._parse_subsections(primary, section.get("text", ""), doc_type)
            if sub_units:
                primary.child_unit_ids = [u.unit_id for u in sub_units]
                units.extend(sub_units)

        return units

    def parse_preamble(self, document: dict, raw_text: str, provenance_map: Dict[str, dict]) -> Optional[LegalUnit]:
        """Extract preamble from a raw act text, if present."""
        m = RE_PREAMBLE.search(raw_text)
        if not m:
            return None
        
        doc_id = document["document_id"]
        prov   = provenance_map.get(doc_id, {})
        
        return LegalUnit(
            unit_id             = f"{doc_id}-UNIT-PREAMBLE",
            document_id         = doc_id,
            version_group_id    = document.get("document_version_group_id"),
            version_id          = document.get("version_label"),
            unit_type           = ChunkType.PREAMBLE,
            section_number      = "0",
            section_title       = "Preamble",
            heading             = "Preamble",
            text                = m.group(1).strip(),
            page_start          = 1,
            page_end            = 1,
            legal_domain        = document.get("legal_domain"),
            document_title      = document.get("title"),
            source_document_id  = doc_id,
            source_sha256       = document.get("sha256"),
            provenance_id       = prov.get("provenance_id"),
            local_file          = prov.get("local_file"),
            synthetic           = True,
            source_authority    = "SYNTHETIC",
            estimated_tokens    = _count_tokens(m.group(1).strip()),
        )

    def _parse_chapter(self, chapter_raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Parse 'Chapter I: Preliminary' → ('I', 'Preliminary')"""
        if not chapter_raw:
            return None, None
        
        # Pattern: "Chapter <num>: <title>" or "Chapter <num>. <title>"
        m = re.match(r"Chapter\s+([IVXivx\d]+)[:\.\s]+(.+)", chapter_raw)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None, chapter_raw.strip()

    def _parse_subsections(
        self,
        parent: LegalUnit,
        text: str,
        doc_type: str,
    ) -> List[LegalUnit]:
        """
        Extract numbered subsections (1), (2) from a section's text.
        Only produces sub-units if at least 2 subsections are found.
        """
        matches = list(RE_NUMBERED_SUBSECTION.finditer(text))
        if len(matches) < 2:
            return []

        sub_units = []
        for idx, m in enumerate(matches):
            sub_num = m.group(1)  # "1", "2"
            sub_text = m.group(2).strip()
            
            chunk_type = ChunkType.SUBSECTION if doc_type in ("act", "amendment") else ChunkType.SUB_RULE

            su = LegalUnit(
                unit_id             = f"{parent.unit_id}-SS{sub_num}",
                document_id         = parent.document_id,
                version_group_id    = parent.version_group_id,
                version_id          = parent.version_id,
                unit_type           = chunk_type,
                chapter_number      = parent.chapter_number,
                chapter_title       = parent.chapter_title,
                section_number      = parent.section_number,
                section_title       = parent.section_title,
                subsection_number   = sub_num,
                heading             = f"Section {parent.section_number}({sub_num})",
                text                = sub_text,
                page_start          = parent.page_start,
                page_end            = parent.page_end,
                legal_domain        = parent.legal_domain,
                document_title      = parent.document_title,
                act_year            = parent.act_year,
                jurisdiction        = parent.jurisdiction,
                parent_unit_id      = parent.unit_id,
                source_document_id  = parent.source_document_id,
                source_sha256       = parent.source_sha256,
                provenance_id       = parent.provenance_id,
                local_file          = parent.local_file,
                synthetic           = True,
                source_authority    = "SYNTHETIC",
                estimated_tokens    = _count_tokens(sub_text),
            )
            sub_units.append(su)

        return sub_units


# ──────────────────────────────────────────────
# Definition Extractor
# ──────────────────────────────────────────────

def extract_definitions(section: dict, document: dict) -> List[dict]:
    """
    Extract legal term definitions from a section's text.
    Returns a list of partial DefinitionRecord dicts.
    """
    text     = section.get("text", "")
    doc_id   = document["document_id"]
    sec_id   = section.get("section_id")
    ver_id   = section.get("version_id") or document.get("version_label")
    page_s   = section.get("page_start")
    page_e   = section.get("page_end")
    
    defs = []
    seen_terms: set = set()

    for pattern in (RE_DEFINITION_QUOTED, RE_DEFINITION_SINGLE, RE_DEFINITION_DASH):
        for m in pattern.finditer(text):
            term = m.group(1).strip()
            if term.lower() in seen_terms:
                continue
            seen_terms.add(term.lower())
            defs.append({
                "document_id":       doc_id,
                "version_id":        ver_id,
                "term":              term,
                "definition_text":   m.group(2).strip(),
                "source_section_id": sec_id,
                "page_start":        page_s,
                "page_end":          page_e,
                "synthetic":         True,
                "source_authority":  "SYNTHETIC",
            })

    return defs


# ──────────────────────────────────────────────
# Cross-Reference Extractor
# ──────────────────────────────────────────────

_CROSSREF_PATTERNS = [
    (RE_CROSSREF_SECTION,   "SECTION_REFERENCE"),
    (RE_CROSSREF_RULE,      "RULE_REFERENCE"),
    (RE_CROSSREF_ARTICLE,   "ARTICLE_REFERENCE"),
    (RE_CROSSREF_ACT,       "ACT_REFERENCE"),
    (RE_CROSSREF_CLAUSE,    "CLAUSE_REFERENCE"),
]


def extract_cross_references(
    unit: LegalUnit,
    existing_doc_ids: set,
) -> List[dict]:
    """
    Extract cross-references from a LegalUnit's text.
    Attempts to resolve SYN-ACT-XXX references.
    Returns a list of partial CrossReferenceRecord dicts.
    """
    text = unit.text
    refs = []
    seen: set = set()

    for pattern, ref_type in _CROSSREF_PATTERNS:
        for m in pattern.finditer(text):
            raw = m.group(0)
            if raw in seen:
                continue
            seen.add(raw)

            resolved_doc: Optional[str] = None
            if ref_type == "ACT_REFERENCE":
                doc_key = f"SYN-ACT-{m.group(1)}"
                if doc_key in existing_doc_ids:
                    resolved_doc = doc_key

            refs.append({
                "source_unit_id":            unit.unit_id,
                "source_document_id":         unit.document_id,
                "target_reference":           raw,
                "reference_type":             ref_type,
                "resolved_target_document_id": resolved_doc,
                "resolved_target_unit_id":    None,
                "confidence":                 0.9 if resolved_doc else 0.5,
                "synthetic":                  True,
                "source_authority":           "SYNTHETIC",
            })

    return refs
