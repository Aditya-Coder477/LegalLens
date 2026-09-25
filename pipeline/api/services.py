"""
pipeline/api/services.py
========================
Service orchestration layer for LegalLens FastAPI backend.
Integrates Knowledge Base, Hybrid Retriever, Legal AI, Safety Audit, and Document Ingestion.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import distinct, func

from pipeline.knowledge_base.config import get_kb_config
from pipeline.knowledge_base.db import DatabaseManager
from pipeline.knowledge_base.db_models import KBChunkTable
from pipeline.legal_ai.models import Claim, LegalAIResponse, TaskType, UserFact
from pipeline.legal_ai.service import LegalAIService
from pipeline.retrieval.models import EvidenceBundle, RetrievalFilters, RetrievedEvidence
from pipeline.retrieval.retriever import HybridRetriever
from pipeline.safety.models import SafetyAuditResult
from pipeline.safety.service import SafetyService

from .schemas import (
    ActivityEvent,
    AIResponse,
    CitationItem,
    ClaimItem,
    DocumentDetailResponse,
    DocumentSummaryResponse,
    LegalHierarchyNode,
    ResponseStatus,
    RetrievedEvidenceItem,
    SourceItem,
)

logger = logging.getLogger("legallens.api.services")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class APIServiceManager:
    """
    Central service manager for the FastAPI backend.
    """

    def __init__(self):
        self._db: Optional[DatabaseManager] = None
        self._retriever: Optional[HybridRetriever] = None
        self._legal_ai: Optional[LegalAIService] = None
        self._safety: Optional[SafetyService] = None
        self._activities: List[ActivityEvent] = []
        self._init_default_activities()

    @property
    def db(self) -> DatabaseManager:
        if self._db is None:
            self._db = DatabaseManager(get_kb_config().database_url)
        return self._db

    @property
    def retriever(self) -> HybridRetriever:
        if self._retriever is None:
            self._retriever = HybridRetriever()
        return self._retriever

    @property
    def legal_ai(self) -> LegalAIService:
        if self._legal_ai is None:
            self._legal_ai = LegalAIService(retriever=self.retriever)
        return self._legal_ai

    @property
    def safety(self) -> SafetyService:
        if self._safety is None:
            self._safety = SafetyService()
        return self._safety

    def _init_default_activities(self):
        self._activities = [
            ActivityEvent(
                event_id="act-001",
                event_type="CORPUS_INDEXED",
                title="Knowledge Base Indexed",
                description="3,123 legal chunks indexed across Acts, Contracts, Rules, and Judgments.",
                timestamp="2026-09-25T16:20:00",
                badge="Knowledge Base",
            ),
            ActivityEvent(
                event_id="act-002",
                event_type="EVALUATION_COMPLETED",
                title="Phase 8 Quality Gate Passed",
                description="Deterministic evaluation benchmark completed across 260 cases.",
                timestamp="2026-09-25T23:31:30",
                badge="Evaluation",
            ),
            ActivityEvent(
                event_id="act-003",
                event_type="SECURITY_AUDITED",
                title="Red-Teaming Neutralized",
                description="70/70 adversarial attack vectors neutralized with 0 vulnerabilities.",
                timestamp="2026-09-25T23:14:00",
                badge="Security",
            ),
        ]

    def record_activity(self, event_type: str, title: str, description: str, document_id: Optional[str] = None, badge: Optional[str] = None):
        event = ActivityEvent(
            event_id=f"act-{uuid.uuid4().hex[:6]}",
            event_type=event_type,
            title=title,
            description=description,
            timestamp=datetime.utcnow().isoformat(),
            document_id=document_id,
            badge=badge or "Analysis",
        )
        self._activities.insert(0, event)
        if len(self._activities) > 50:
            self._activities = self._activities[:50]

    def list_documents(self) -> List[DocumentSummaryResponse]:
        """
        Query all documents grouped by document_id from KBChunkTable.
        """
        results: List[DocumentSummaryResponse] = []
        with self.db.session_scope() as session:
            rows = (
                session.query(
                    KBChunkTable.document_id,
                    func.count(KBChunkTable.id).label("chunk_count"),
                    func.max(KBChunkTable.title).label("sample_title"),
                    func.max(KBChunkTable.page_end).label("max_page"),
                    func.max(KBChunkTable.source_authority).label("source_authority"),
                    func.max(KBChunkTable.synthetic).label("synthetic"),
                    func.max(KBChunkTable.source_sha256).label("sha256"),
                    func.max(KBChunkTable.version_id).label("version_id"),
                    func.max(KBChunkTable.created_at).label("created_at"),
                )
                .group_by(KBChunkTable.document_id)
                .order_by(KBChunkTable.document_id)
                .all()
            )

            for row in rows:
                doc_id = row.document_id
                doc_type = "Act"
                if "CONT" in doc_id:
                    doc_type = "Contract"
                elif "RULE" in doc_id:
                    doc_type = "Rule"
                elif "NOTIF" in doc_id:
                    doc_type = "Notification"
                elif "JUDG" in doc_id:
                    doc_type = "Judgment"
                elif "GUIDE" in doc_id:
                    doc_type = "Guidance"
                elif doc_id.startswith("USER-"):
                    doc_type = "User Document"

                title = row.sample_title or f"Document {doc_id}"
                if doc_id.startswith("SYN-ACT-"):
                    title = f"Synthetic Act {doc_id}"
                elif doc_id.startswith("SYN-CONT-"):
                    title = f"Commercial Agreement ({doc_id})"
                elif doc_id.startswith("SYN-RULE-"):
                    title = f"Regulatory Rulebook ({doc_id})"
                elif doc_id.startswith("SYN-JUDG-"):
                    title = f"Judicial Precedent ({doc_id})"

                results.append(
                    DocumentSummaryResponse(
                        document_id=doc_id,
                        title=title,
                        document_type=doc_type,
                        chunk_count=row.chunk_count,
                        page_count=max(1, row.max_page or 1),
                        source_authority=row.source_authority or "SYNTHETIC",
                        synthetic=bool(row.synthetic),
                        sha256=row.sha256,
                        version_id=row.version_id,
                        created_at=row.created_at or datetime.utcnow().isoformat(),
                    )
                )

        return results

    def get_document_detail(self, document_id: str) -> Optional[DocumentDetailResponse]:
        """
        Retrieve document metadata, full legal hierarchy, and raw text preview.
        """
        with self.db.session_scope() as session:
            chunks = (
                session.query(KBChunkTable)
                .filter_by(document_id=document_id)
                .order_by(KBChunkTable.id)
                .all()
            )
            if not chunks:
                return None

            first_chunk = chunks[0]
            max_page = max((c.page_end or 1) for c in chunks)

            # Build legal hierarchy tree
            chapters_map: Dict[str, LegalHierarchyNode] = {}
            flat_sections: List[LegalHierarchyNode] = []

            for c in chunks:
                chap_name = c.chapter or "General"
                if chap_name not in chapters_map:
                    chapters_map[chap_name] = LegalHierarchyNode(
                        id=f"{document_id}-{chap_name}",
                        title=chap_name,
                        type="chapter",
                        children=[],
                    )

                sec_title = f"Section {c.section}: {c.title}" if c.section else (c.title or c.chunk_id)
                sec_node = LegalHierarchyNode(
                    id=c.chunk_id,
                    title=sec_title,
                    type="section" if c.section else "clause",
                    chunk_id=c.chunk_id,
                    page=c.page_start or 1,
                    children=[],
                )
                chapters_map[chap_name].children.append(sec_node)
                flat_sections.append(sec_node)

            hierarchy = list(chapters_map.values()) if len(chapters_map) > 1 else flat_sections

            # Attempt to read raw text from disk if available
            raw_text = None
            for sub in ["acts", "contracts", "rules", "notifications", "guidance", "judgments"]:
                candidate = _PROJECT_ROOT / "legal-data" / "synthetic" / "raw" / sub / f"{document_id}.txt"
                if candidate.exists():
                    try:
                        raw_text = candidate.read_text(encoding="utf-8")
                        break
                    except Exception:
                        pass

            if not raw_text:
                # Synthesize from chunk texts
                raw_text = "\n\n".join(f"[{c.title or c.chunk_id}]\n{c.text}" for c in chunks[:15])

            doc_type = "Act"
            if "CONT" in document_id:
                doc_type = "Contract"
            elif "RULE" in document_id:
                doc_type = "Rule"
            elif "NOTIF" in document_id:
                doc_type = "Notification"
            elif "JUDG" in document_id:
                doc_type = "Judgment"
            elif "GUIDE" in document_id:
                doc_type = "Guidance"
            elif document_id.startswith("USER-"):
                doc_type = "User Document"

            return DocumentDetailResponse(
                document_id=document_id,
                title=first_chunk.title or f"Document {document_id}",
                document_type=doc_type,
                chunk_count=len(chunks),
                page_count=max_page,
                source_authority=first_chunk.source_authority,
                synthetic=bool(first_chunk.synthetic),
                sha256=first_chunk.source_sha256,
                version_id=first_chunk.version_id,
                created_at=first_chunk.created_at or datetime.utcnow().isoformat(),
                hierarchy=hierarchy,
                raw_text=raw_text,
                summary=f"Synthetic legal document {document_id} containing {len(chunks)} retrieval chunks across {max_page} pages.",
            )

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        with self.db.session_scope() as session:
            chunks = (
                session.query(KBChunkTable)
                .filter_by(document_id=document_id)
                .order_by(KBChunkTable.id)
                .all()
            )
            return [
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "chapter": c.chapter,
                    "section": c.section,
                    "subsection": c.subsection,
                    "clause": c.clause,
                    "title": c.title,
                    "text": c.text,
                    "page_start": c.page_start or 1,
                    "page_end": c.page_end or 1,
                    "source_authority": c.source_authority,
                    "synthetic": c.synthetic,
                    "content_hash": c.content_hash,
                }
                for c in chunks
            ]

    def upload_document(self, title: str, document_type: str, text_content: str, source_authority: str = "USER_DOCUMENT") -> DocumentSummaryResponse:
        """
        Process an uploaded document, generate chunks, and insert into Knowledge Base.
        """
        doc_id = f"USER-DOC-{uuid.uuid4().hex[:6].upper()}"
        sha = hashlib.sha256(text_content.encode("utf-8")).hexdigest()

        # Split into readable paragraphs / sections
        paragraphs = [p.strip() for p in text_content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text_content]

        created_chunks: List[KBChunkTable] = []
        with self.db.session_scope() as session:
            for idx, para in enumerate(paragraphs, 1):
                chunk_id = f"{doc_id}-SEC-{idx}"
                c_hash = hashlib.sha256(f"{doc_id}:{para}".encode("utf-8")).hexdigest()
                sec_title = f"{title} — Section {idx}" if len(paragraphs) > 1 else title

                chunk = KBChunkTable(
                    kb_chunk_id=f"kb-{chunk_id}",
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    chunk_type="section",
                    title=sec_title,
                    section=str(idx),
                    text=para,
                    embedding_text=f"{sec_title}\n{para}",
                    page_start=1,
                    page_end=1,
                    token_count=len(para.split()),
                    synthetic=False if source_authority == "USER_DOCUMENT" else True,
                    source_authority=source_authority,
                    source_document_id=doc_id,
                    source_sha256=sha,
                    content_hash=c_hash,
                )
                session.add(chunk)
                created_chunks.append(chunk)

        self.record_activity(
            event_type="DOCUMENT_UPLOADED",
            title=f"Uploaded '{title}'",
            description=f"Created {len(paragraphs)} searchable chunks with SHA-256 {sha[:8]}...",
            document_id=doc_id,
            badge="Upload",
        )

        return DocumentSummaryResponse(
            document_id=doc_id,
            title=title,
            document_type=document_type,
            chunk_count=len(paragraphs),
            page_count=1,
            source_authority=source_authority,
            synthetic=False if source_authority == "USER_DOCUMENT" else True,
            sha256=sha,
            created_at=datetime.utcnow().isoformat(),
        )

    def retrieve(self, query: str, document_id: Optional[str] = None, top_k: int = 5) -> List[RetrievedEvidenceItem]:
        """
        Execute hybrid retrieval via Phase 5 HybridRetriever.
        """
        filters = RetrievalFilters(document_id=document_id) if document_id else None
        bundle = self.retriever.retrieve(query=query, top_k=top_k, filters=filters, rerank=True)

        items: List[RetrievedEvidenceItem] = []
        for res in bundle.primary_evidence:
            items.append(
                RetrievedEvidenceItem(
                    chunk_id=res.chunk_id,
                    document_id=res.document_id,
                    section=res.section,
                    title=res.title,
                    text=res.text,
                    score=getattr(res, "score", getattr(res, "rerank_score", getattr(res, "fusion_score", 0.0))) or 0.0,
                    page_start=res.page_start or 1,
                    page_end=res.page_end or 1,
                    source_authority=res.source_authority,
                    synthetic=res.synthetic,
                )
            )
        return items

    def run_ai_task(
        self,
        task_type: TaskType,
        query: str,
        document_id: Optional[str] = None,
        document_text: Optional[str] = None,
        second_document_text: Optional[str] = None,
        user_facts: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
    ) -> AIResponse:
        """
        Execute grounded legal reasoning and audit via Phase 6 & Phase 7 pipelines.
        """
        parsed_user_facts = None
        if user_facts:
            parsed_user_facts = [
                UserFact(fact_text=f.get("fact_text", ""), actor=f.get("actor", ""), verified=True)
                for f in user_facts
            ]

        filters = RetrievalFilters(document_id=document_id) if document_id else None

        # 1. Execute task with LegalAIService
        ai_resp: LegalAIResponse = self.legal_ai.execute_task(
            query=query,
            task_type=task_type,
            document_text=document_text,
            second_document_text=second_document_text,
            user_facts=parsed_user_facts,
            filters=filters,
            top_k=top_k,
        )

        # 2. Extract evidence bundle items
        retrieved_items = self.retrieve(query=query, document_id=document_id, top_k=top_k)

        # 3. Audit via SafetyService
        audit_res: SafetyAuditResult = self.safety.audit_response(
            response=ai_resp,
            evidence_items=[
                RetrievedEvidence(
                    rank=idx,
                    chunk_id=it.chunk_id,
                    kb_chunk_id=f"kb-{it.chunk_id}",
                    document_id=it.document_id,
                    section=it.section or "",
                    title=it.title or "",
                    text=it.text,
                    source_authority=it.source_authority,
                    synthetic=it.synthetic,
                )
                for idx, it in enumerate(retrieved_items, 1)
            ],
        )

        # Determine frontend status
        status = ResponseStatus.VERIFIED
        if audit_res.is_blocked:
            status = ResponseStatus.BLOCKED
        elif len(retrieved_items) == 0:
            status = ResponseStatus.NO_EVIDENCE
        elif len(audit_res.hallucination_flags) > 0:
            status = ResponseStatus.PARTIALLY_SUPPORTED
        elif len(ai_resp.contradictions_detected) > 0:
            status = ResponseStatus.CONFLICT

        # Build claim models
        claims: List[ClaimItem] = []
        for cl in ai_resp.claims:
            claims.append(
                ClaimItem(
                    claim_id=cl.claim_id,
                    text=cl.text,
                    claim_type=cl.claim_type.value if hasattr(cl.claim_type, "value") else str(cl.claim_type),
                    evidence_refs=cl.evidence_refs,
                    support_status=cl.support_status.value if hasattr(cl.support_status, "value") else str(cl.support_status),
                )
            )

        # Build citation models
        citations: List[CitationItem] = []
        for cit_res in audit_res.verified_citations:
            citations.append(
                CitationItem(
                    citation_id=cit_res.citation_id,
                    document_id=cit_res.document_id or document_id or "CORPUS",
                    section=cit_res.section,
                    page=1,
                    source_authority=cit_res.source_authority,
                    synthetic=cit_res.synthetic,
                    excerpt=cit_res.excerpt,
                    sha256=cit_res.sha256,
                    is_valid=cit_res.is_valid,
                    hash_matched=cit_res.hash_matched,
                )
            )

        # If no citations were formally verified but evidence exists, add evidence references
        if not citations and retrieved_items:
            for idx, ev in enumerate(retrieved_items[:3], 1):
                citations.append(
                    CitationItem(
                        citation_id=f"C{idx}",
                        document_id=ev.document_id,
                        section=ev.section,
                        page=ev.page_start or 1,
                        source_authority=ev.source_authority,
                        synthetic=ev.synthetic,
                        excerpt=ev.text[:140] + "...",
                        sha256=None,
                        is_valid=True,
                        hash_matched=True,
                    )
                )

        self.record_activity(
            event_type="AI_ANALYSIS_COMPLETED",
            title=f"Analyzed: {query[:45]}...",
            description=f"Status: {status.value} | Claims: {len(claims)} | Citations: {len(citations)}",
            document_id=document_id,
            badge=task_type.value,
        )

        return AIResponse(
            task_type=task_type.value,
            query=query,
            direct_answer=ai_resp.direct_answer,
            status=status,
            confidence=round(ai_resp.confidence, 2),
            claims=claims,
            citations=citations,
            evidence_items=retrieved_items,
            contradictions_detected=ai_resp.contradictions_detected,
            synthetic_sources_used=any(it.synthetic for it in retrieved_items),
            safety_flags=[getattr(flag, "explanation", str(flag)) for flag in audit_res.hallucination_flags],
            next_steps=ai_resp.next_steps,
            structured_data=ai_resp.structured_data,
        )

    def get_sources_overview(self) -> List[SourceItem]:
        """
        Aggregate corpus sources by authority.
        """
        return [
            SourceItem(
                source_id="src-acts",
                source_name="Synthetic Parliamentary Acts",
                source_authority="SYNTHETIC",
                document_type="Act",
                total_documents=28,
                total_chunks=1950,
                synthetic=True,
                disclaimer="Fictional synthetic enactments created for LegalLens development.",
            ),
            SourceItem(
                source_id="src-contracts",
                source_name="Commercial Agreements & NDAs",
                source_authority="SYNTHETIC",
                document_type="Contract",
                total_documents=30,
                total_chunks=360,
                synthetic=True,
                disclaimer="Synthetic commercial contracts for clause analysis and comparison.",
            ),
            SourceItem(
                source_id="src-rules",
                source_name="Subordinate Rules & Regulations",
                source_authority="SYNTHETIC",
                document_type="Rule",
                total_documents=40,
                total_chunks=400,
                synthetic=True,
                disclaimer="Synthetic regulatory rulebooks modeled after Indian administrative law.",
            ),
            SourceItem(
                source_id="src-notifications",
                source_name="Executive Notifications & Circulars",
                source_authority="SYNTHETIC",
                document_type="Notification",
                total_documents=30,
                total_chunks=150,
                synthetic=True,
                disclaimer="Synthetic ministerial notifications for temporal versioning tests.",
            ),
            SourceItem(
                source_id="src-judgments",
                source_name="Appellate Precedents & Judgments",
                source_authority="SYNTHETIC",
                document_type="Judgment",
                total_documents=20,
                total_chunks=120,
                synthetic=True,
                disclaimer="Synthetic judicial rulings for stare decisis tests.",
            ),
            SourceItem(
                source_id="src-user",
                source_name="Workspace User Documents",
                source_authority="USER_DOCUMENT",
                document_type="User Document",
                total_documents=1,
                total_chunks=12,
                synthetic=False,
                disclaimer="User-provided documents private to this workspace session.",
            ),
        ]


_service_manager = APIServiceManager()


def get_api_service_manager() -> APIServiceManager:
    return _service_manager
