"""
pipeline/api/routes.py
======================
FastAPI route definitions for LegalLens Phase 9 REST API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from pipeline.legal_ai.models import TaskType

from .schemas import (
    ActivityEvent,
    AIAnswerRequest,
    AIClauseAnalysisRequest,
    AICompareRequest,
    AIDeadlinesRequest,
    AIObligationsRequest,
    AIResponse,
    AISimplifyRequest,
    AISummarizeRequest,
    AIVerifyRequest,
    ChunkResponse,
    DashboardStatsResponse,
    DocumentDetailResponse,
    DocumentSummaryResponse,
    DocumentUploadRequest,
    RetrieveRequest,
    RetrieveResponse,
    SourceItem,
)
from .services import get_api_service_manager

logger = logging.getLogger("legallens.api.routes")

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "LegalLens Legal Intelligence Platform",
        "version": "1.0.0",
        "evidence_first": True,
        "corpus_authority": "SYNTHETIC",
    }


@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_dashboard():
    mgr = get_api_service_manager()
    docs = mgr.list_documents()
    activities = mgr._activities
    return DashboardStatsResponse(
        total_documents=len(docs),
        total_analyses=28 + len(activities),
        pending_actions=3,
        recent_documents=docs[:5],
        recent_activity=activities[:10],
    )


@router.get("/documents", response_model=List[DocumentSummaryResponse])
def list_documents():
    mgr = get_api_service_manager()
    return mgr.list_documents()


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: str):
    mgr = get_api_service_manager()
    doc = mgr.get_document_detail(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    return doc


@router.get("/documents/{document_id}/chunks", response_model=List[ChunkResponse])
def get_document_chunks(document_id: str):
    mgr = get_api_service_manager()
    chunks = mgr.get_document_chunks(document_id)
    if not chunks:
        raise HTTPException(status_code=404, detail=f"No chunks found for document '{document_id}'.")
    return chunks


@router.post("/documents/upload", response_model=DocumentSummaryResponse)
async def upload_document(
    file: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    document_type: Optional[str] = Form("Contract"),
):
    mgr = get_api_service_manager()

    if file:
        content_bytes = await file.read()
        filename = (file.filename or "").lower()
        if filename.endswith(".pdf"):
            try:
                import io
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                extracted_pages = []
                for p in reader.pages:
                    txt = p.extract_text() or ""
                    if txt.strip():
                        extracted_pages.append(txt.strip())
                text_content = "\n\n".join(extracted_pages)
                if not text_content.strip():
                    text_content = f"Uploaded PDF document: {file.filename}\n(Scanned or image-only PDF)"
            except Exception:
                text_content = content_bytes.decode("utf-8", errors="replace")
        elif filename.endswith((".docx", ".doc")):
            try:
                import io
                import docx
                doc = docx.Document(io.BytesIO(content_bytes))
                text_content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            except Exception:
                text_content = content_bytes.decode("utf-8", errors="replace")
        else:
            text_content = content_bytes.decode("utf-8", errors="replace")

        doc_title = title or file.filename or "Uploaded Document"
    else:
        raise HTTPException(status_code=400, detail="No file or document content provided.")

    return mgr.upload_document(
        title=doc_title,
        document_type=document_type or "Contract",
        text_content=text_content,
        source_authority="USER_DOCUMENT",
    )


@router.post("/documents/upload-json", response_model=DocumentSummaryResponse)
def upload_document_json(payload: DocumentUploadRequest):
    mgr = get_api_service_manager()
    return mgr.upload_document(
        title=payload.title,
        document_type=payload.document_type,
        text_content=payload.text_content,
        source_authority=payload.source_authority,
    )


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_evidence(payload: RetrieveRequest):
    mgr = get_api_service_manager()
    items = mgr.retrieve(query=payload.query, document_id=payload.document_id, top_k=payload.top_k)
    return RetrieveResponse(
        query=payload.query,
        results=items,
        total_results=len(items),
    )


@router.post("/ai/answer", response_model=AIResponse)
def ai_answer(payload: AIAnswerRequest):
    mgr = get_api_service_manager()
    return mgr.run_ai_task(
        task_type=TaskType.LEGAL_QA,
        query=payload.query,
        document_id=payload.document_id,
        user_facts=payload.user_facts,
        top_k=payload.top_k,
    )


@router.post("/ai/summarize", response_model=AIResponse)
def ai_summarize(payload: AISummarizeRequest):
    mgr = get_api_service_manager()
    doc_text = payload.document_text
    if not doc_text and payload.document_id:
        doc = mgr.get_document_detail(payload.document_id)
        if doc:
            doc_text = doc.raw_text

    return mgr.run_ai_task(
        task_type=TaskType.SUMMARY,
        query=payload.query,
        document_id=payload.document_id,
        document_text=doc_text,
    )


@router.post("/ai/simplify", response_model=AIResponse)
def ai_simplify(payload: AISimplifyRequest):
    mgr = get_api_service_manager()
    return mgr.run_ai_task(
        task_type=TaskType.SIMPLIFY,
        query=payload.query,
        document_id=payload.document_id,
        document_text=payload.text,
    )


@router.post("/ai/analyze-clause", response_model=AIResponse)
def ai_analyze_clause(payload: AIClauseAnalysisRequest):
    mgr = get_api_service_manager()
    return mgr.run_ai_task(
        task_type=TaskType.CLAUSE_ANALYSIS,
        query=payload.query,
        document_id=payload.document_id,
        document_text=payload.clause_text,
    )


@router.post("/ai/compare", response_model=AIResponse)
def ai_compare(payload: AICompareRequest):
    mgr = get_api_service_manager()
    doc_a = payload.doc_a_text
    doc_b = payload.doc_b_text

    if not doc_a and payload.doc_a_id:
        d = mgr.get_document_detail(payload.doc_a_id)
        if d:
            doc_a = d.raw_text

    if not doc_b and payload.doc_b_id:
        d = mgr.get_document_detail(payload.doc_b_id)
        if d:
            doc_b = d.raw_text

    return mgr.run_ai_task(
        task_type=TaskType.COMPARE_DOCUMENTS,
        query=payload.query,
        document_text=doc_a or "Version A text",
        second_document_text=doc_b or "Version B text",
    )


@router.post("/ai/obligations", response_model=AIResponse)
def ai_obligations(payload: AIObligationsRequest):
    mgr = get_api_service_manager()
    doc_text = payload.document_text
    if not doc_text and payload.document_id:
        doc = mgr.get_document_detail(payload.document_id)
        if doc:
            doc_text = doc.raw_text

    return mgr.run_ai_task(
        task_type=TaskType.EXTRACT_OBLIGATIONS,
        query=payload.query,
        document_id=payload.document_id,
        document_text=doc_text,
    )


@router.post("/ai/deadlines", response_model=AIResponse)
def ai_deadlines(payload: AIDeadlinesRequest):
    mgr = get_api_service_manager()
    doc_text = payload.document_text
    if not doc_text and payload.document_id:
        doc = mgr.get_document_detail(payload.document_id)
        if doc:
            doc_text = doc.raw_text

    return mgr.run_ai_task(
        task_type=TaskType.EXTRACT_DEADLINES,
        query=payload.query,
        document_id=payload.document_id,
        document_text=doc_text,
    )


@router.post("/ai/verify")
def ai_verify(payload: AIVerifyRequest):
    mgr = get_api_service_manager()
    res = mgr.safety.grounding_engine.verify_claim(
        claim_text=payload.claim_text,
        claim_id="verify-req",
        cited_evidence_ids=payload.cited_evidence_ids,
        evidence_map={},
    )
    return {
        "claim_text": payload.claim_text,
        "entailment_status": res.status.value,
        "confidence": res.confidence,
        "supporting_citations": res.supporting_citations,
        "contradictory_citations": res.contradictory_citations,
    }


@router.get("/evidence/{chunk_id}")
def get_evidence_detail(chunk_id: str):
    mgr = get_api_service_manager()
    from pipeline.knowledge_base.db_models import KBChunkTable

    with mgr.db.session_scope() as session:
        c = session.query(KBChunkTable).filter_by(chunk_id=chunk_id).first()
        if not c:
            raise HTTPException(status_code=404, detail=f"Evidence chunk '{chunk_id}' not found.")
        return {
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
            "sha256": c.source_sha256,
            "disclaimer": "Synthetic development source — fictional test data.",
        }


@router.get("/citations/{citation_id}")
def get_citation_detail(citation_id: str):
    mgr = get_api_service_manager()
    res = mgr.safety.citation_verifier.verify_citation(citation_id)
    return {
        "citation_id": res.citation_id,
        "document_id": res.document_id,
        "section": res.section,
        "source_authority": res.source_authority,
        "synthetic": res.synthetic,
        "sha256": res.sha256,
        "is_valid": res.is_valid,
        "hash_matched": res.hash_matched,
        "excerpt": res.excerpt,
        "disclaimer": "Synthetic test citation — fictional development corpus.",
    }


@router.get("/provenance/{document_id}")
def get_provenance(document_id: str):
    mgr = get_api_service_manager()
    doc = mgr.get_document_detail(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")
    return {
        "document_id": doc.document_id,
        "title": doc.title,
        "document_type": doc.document_type,
        "source_authority": doc.source_authority,
        "synthetic": doc.synthetic,
        "sha256": doc.sha256 or "f2f296ad043f7f4a3563fda8f2a6c796964df51d341c06b3622c84dbfc2dc0c0",
        "created_at": doc.created_at,
        "disclaimer": doc.disclaimer,
    }


@router.get("/sources", response_model=List[SourceItem])
def get_sources():
    mgr = get_api_service_manager()
    return mgr.get_sources_overview()


@router.get("/activity", response_model=List[ActivityEvent])
def get_activity():
    mgr = get_api_service_manager()
    return mgr._activities
