"""
pipeline/safety/citation_verifier.py
====================================
Formal citation verification and legal provenance resolution engine for LegalLens Phase 7.
Resolves and validates citations against stored Knowledge Base chunks, SHA-256 hashes,
document versions, and statutory catalogues. Detects fabricated and dead citations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from pipeline.knowledge_base.config import get_kb_config
from pipeline.knowledge_base.db import DatabaseManager
from pipeline.knowledge_base.db_models import KBChunkTable
from pipeline.retrieval.models import RetrievedEvidence

from .config import SafetyConfig, get_safety_config
from .models import CitationVerificationResult, CitationVerificationStatus


class CitationVerifier:
    """
    Validates legal citations against the immutable Knowledge Base and provenance records.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        config: Optional[SafetyConfig] = None,
    ):
        self.config = config or get_safety_config()
        if db_manager:
            self.db = db_manager
        else:
            kb_cfg = get_kb_config()
            self.db = DatabaseManager(kb_cfg.database_url)

    def extract_citations_from_text(self, text: str) -> List[str]:
        """
        Extract both short evidence tags ([E1], E2) and statutory/contractual citations
        such as 'Section 18 of SYN-ACT-005', 'Clause 7 of SYN-CONT-002', 'Rule 10 of SYN-RULE-002'.
        """
        found: Set[str] = set()

        # 1. Short evidence tags: [E1], E1
        for m in re.finditer(r"\b(E\d+)\b", text):
            found.add(m.group(1))

        # 2. Section / Rule citations: "Section 18 of SYN-ACT-005", "Section 10 of SYN-ACT-010-v2"
        pattern_sec = r"\b(?:Section|Sec\.?|Rule|Clause)\s+(\d+[A-Za-z]?(?:\(\d+\))?)\s+(?:of|under)\s+([A-Z]{3,4}-[A-Z]{3,6}-\d+(?:-v\d+)?)\b"
        for m in re.finditer(pattern_sec, text, re.IGNORECASE):
            found.add(f"{m.group(0).strip()}")

        # 3. Direct document ID mentions: "SYN-ACT-001", "SYN-RULE-005"
        pattern_doc = r"\b(SYN-(?:ACT|RULE|NOTIF|CIRC|ORDER|GUID|CONT)-\d+(?:-v\d+)?)\b"
        for m in re.finditer(pattern_doc, text):
            found.add(m.group(1))

        return sorted(list(found))

    def verify_citation(
        self,
        raw_citation: str,
        evidence_map: Optional[Dict[str, RetrievedEvidence]] = None,
    ) -> CitationVerificationResult:
        """
        Verify a single citation against active evidence context or the global Knowledge Base.
        """
        raw = raw_citation.strip().strip("[]()")
        notes: List[str] = []

        # Case A: Short Evidence ID (e.g. E1, E2)
        if re.match(r"^E\d+$", raw):
            if evidence_map and raw in evidence_map:
                ev = evidence_map[raw]
                formatted = self._format_citation(
                    doc_id=ev.document_id,
                    title=ev.title,
                    section=ev.section,
                    authority=ev.source_authority,
                    version_id=ev.version_id,
                )
                return CitationVerificationResult(
                    raw_citation=raw,
                    status=CitationVerificationStatus.VERIFIED,
                    resolved_chunk_id=ev.chunk_id,
                    resolved_document_id=ev.document_id,
                    resolved_section=ev.section,
                    source_sha256=ev.source_sha256,
                    provenance_id=ev.provenance_id,
                    source_authority=ev.source_authority,
                    is_synthetic=ev.synthetic,
                    formatted_legal_citation=formatted,
                    verification_notes=["Resolved successfully from retrieved EvidenceBundle context."],
                )
            else:
                return CitationVerificationResult(
                    raw_citation=raw,
                    status=CitationVerificationStatus.UNRESOLVED,
                    verification_notes=[f"Evidence identifier '{raw}' is not present in retrieved context."],
                )

        # Case B: Specific Section of Document (e.g. "Section 18 of SYN-ACT-005", "Section 999 of SYN-ACT-001")
        sec_match = re.search(
            r"(?:Section|Sec\.?|Rule|Clause)\s+(\d+[A-Za-z]?(?:\(\d+\))?)\s+(?:of|under)\s+([A-Za-z0-9_-]+)",
            raw,
            re.IGNORECASE,
        )
        if sec_match:
            sec_num = sec_match.group(1).split("(")[0]  # Base section number
            doc_id = sec_match.group(2).upper()
            return self._verify_section_in_kb(raw, doc_id, sec_num)

        # Case C: Standalone Document ID (e.g. "SYN-ACT-001")
        if re.match(r"^SYN-[A-Za-z0-9_-]+$", raw, re.IGNORECASE):
            return self._verify_document_in_kb(raw, raw.upper())

        # Case D: Unparseable citation string
        return CitationVerificationResult(
            raw_citation=raw,
            status=CitationVerificationStatus.UNRESOLVED,
            verification_notes=["Unable to parse legal provision or document reference structure."],
        )

    def verify_all_citations(
        self,
        citations: List[str],
        text_content: str = "",
        evidence_map: Optional[Dict[str, RetrievedEvidence]] = None,
    ) -> List[CitationVerificationResult]:
        """
        Verify an aggregated list of citations and any citations detected in text.
        """
        all_refs = set(citations)
        if text_content:
            all_refs.update(self.extract_citations_from_text(text_content))

        results = []
        for ref in sorted(list(all_refs)):
            res = self.verify_citation(ref, evidence_map=evidence_map)
            results.append(res)
        return results

    def _verify_section_in_kb(
        self,
        raw_citation: str,
        doc_id: str,
        section_num: str,
    ) -> CitationVerificationResult:
        """
        Query DB to see if the document and specific section exist.
        """
        notes: List[str] = []
        try:
            with self.db.session_scope() as session:
                # 1. Check if document exists at all
                doc_exists = session.query(KBChunkTable).filter(
                    func.upper(KBChunkTable.document_id) == doc_id
                ).first()

                if not doc_exists:
                    return CitationVerificationResult(
                        raw_citation=raw_citation,
                        status=CitationVerificationStatus.FABRICATED,
                        resolved_document_id=doc_id,
                        resolved_section=section_num,
                        verification_notes=[f"Document '{doc_id}' does not exist in the Knowledge Base."],
                    )

                # 2. Check if specific section exists in this document
                chunk = session.query(KBChunkTable).filter(
                    func.upper(KBChunkTable.document_id) == doc_id,
                    KBChunkTable.section == section_num,
                ).first()

                if not chunk:
                    # Section is fabricated / out of bounds (e.g. Section 999)
                    max_sec = session.query(func.max(KBChunkTable.section)).filter(
                        func.upper(KBChunkTable.document_id) == doc_id
                    ).scalar()
                    notes.append(f"Section {section_num} does not exist in {doc_id}.")
                    return CitationVerificationResult(
                        raw_citation=raw_citation,
                        status=CitationVerificationStatus.FABRICATED,
                        resolved_document_id=doc_id,
                        resolved_section=section_num,
                        verification_notes=notes,
                    )

                # 3. Check version status (if an amendment exists)
                is_current = True
                if "-v" in doc_id:
                    pass  # Explicit version requested
                else:
                    # Check if newer version exists in version group
                    newer_v = session.query(KBChunkTable).filter(
                        KBChunkTable.version_group_id == chunk.version_group_id,
                        KBChunkTable.version_id > chunk.version_id,
                    ).first()
                    if newer_v:
                        is_current = False
                        notes.append(f"Notice: Superseded by newer enactment {newer_v.document_id} ({newer_v.version_id}).")

                formatted = self._format_citation(
                    doc_id=chunk.document_id,
                    title=chunk.title,
                    section=chunk.section,
                    authority=chunk.source_authority,
                    version_id=chunk.version_id,
                )

                status = CitationVerificationStatus.VERIFIED if is_current else CitationVerificationStatus.SUPERSEDED_VERSION

                return CitationVerificationResult(
                    raw_citation=raw_citation,
                    status=status,
                    resolved_chunk_id=chunk.chunk_id,
                    resolved_document_id=chunk.document_id,
                    resolved_section=chunk.section,
                    source_sha256=chunk.source_sha256,
                    provenance_id=chunk.provenance_id,
                    source_authority=chunk.source_authority,
                    is_synthetic=chunk.synthetic,
                    is_version_current=is_current,
                    formatted_legal_citation=formatted,
                    verification_notes=notes or ["Verified in knowledge base."],
                )
        except Exception as e:
            return CitationVerificationResult(
                raw_citation=raw_citation,
                status=CitationVerificationStatus.UNRESOLVED,
                verification_notes=[f"Database resolution error: {str(e)}"],
            )

    def _verify_document_in_kb(
        self,
        raw_citation: str,
        doc_id: str,
    ) -> CitationVerificationResult:
        """
        Verify document existence at the enactment level.
        """
        try:
            with self.db.session_scope() as session:
                chunk = session.query(KBChunkTable).filter(
                    func.upper(KBChunkTable.document_id) == doc_id
                ).first()

                if not chunk:
                    return CitationVerificationResult(
                        raw_citation=raw_citation,
                        status=CitationVerificationStatus.FABRICATED,
                        resolved_document_id=doc_id,
                        verification_notes=[f"Document '{doc_id}' not found in Knowledge Base."],
                    )

                formatted = f"{chunk.document_id} ({chunk.source_authority}, Ver: {chunk.version_id or 'original'})"
                return CitationVerificationResult(
                    raw_citation=raw_citation,
                    status=CitationVerificationStatus.VERIFIED,
                    resolved_chunk_id=chunk.chunk_id,
                    resolved_document_id=chunk.document_id,
                    source_sha256=chunk.source_sha256,
                    provenance_id=chunk.provenance_id,
                    source_authority=chunk.source_authority,
                    is_synthetic=chunk.synthetic,
                    formatted_legal_citation=formatted,
                    verification_notes=["Document confirmed in Knowledge Base."],
                )
        except Exception as e:
            return CitationVerificationResult(
                raw_citation=raw_citation,
                status=CitationVerificationStatus.UNRESOLVED,
                verification_notes=[f"Database resolution error: {str(e)}"],
            )

    def _format_citation(
        self,
        doc_id: str,
        title: Optional[str],
        section: Optional[str],
        authority: str,
        version_id: Optional[str],
    ) -> str:
        sec_part = f", § {section}" if section else ""
        ver_part = f" ({version_id})" if version_id else ""
        title_part = f" [{title}]" if title else ""
        return f"{doc_id}{sec_part}{title_part} [{authority}{ver_part}]"
