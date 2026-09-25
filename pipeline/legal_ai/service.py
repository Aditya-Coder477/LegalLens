"""
pipeline/legal_ai/service.py
============================
Master Legal AI Intelligence Service Facade for LegalLens.
Orchestrates Task Classification, Hybrid Retrieval, Delimited Context Building,
Prompt Construction, LLM Execution, and Evidence Grounding Validation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from pipeline.retrieval.models import EvidenceBundle, RetrievalFilters, RetrievedEvidence
from pipeline.retrieval.retriever import HybridRetriever

from .config import LegalAIConfig, get_ai_config
from .context_builder import BuiltContext, ContextBuilder
from .llm_provider import LLMProvider, get_llm_provider
from .models import LegalAIResponse, TaskType, UserFact
from .prompt_builder import PromptBuilder
from .task_classifier import TaskClassifier
from .validator import ResponseValidator


class LegalAIService:
    """
    Main service coordinating all Phase 6 legal reasoning features.
    """

    def __init__(
        self,
        retriever: Optional[HybridRetriever] = None,
        llm_provider: Optional[LLMProvider] = None,
        config: Optional[LegalAIConfig] = None,
    ):
        self.config = config or get_ai_config()
        self.retriever = retriever or HybridRetriever()
        self.llm_provider = llm_provider or get_llm_provider(self.config)
        self.classifier = TaskClassifier()
        self.context_builder = ContextBuilder(max_tokens=self.config.max_context_tokens)
        self.prompt_builder = PromptBuilder()
        self.validator = ResponseValidator(self.config)

    def execute_task(
        self,
        query: str,
        task_type: Optional[TaskType] = None,
        document_text: Optional[str] = None,
        second_document_text: Optional[str] = None,
        user_facts: Optional[List[UserFact]] = None,
        filters: Optional[RetrievalFilters] = None,
        top_k: Optional[int] = None,
    ) -> LegalAIResponse:
        """
        Execute an end-to-end grounded legal AI task.
        """
        # 1. Classify task if not explicitly provided
        effective_task = task_type or self.classifier.classify(query)

        # 2. Retrieve evidence from knowledge base (or build synthetic bundle from document text)
        bundle, additional_evidence = self._prepare_evidence(
            query=query,
            document_text=document_text,
            second_document_text=second_document_text,
            filters=filters,
            top_k=top_k,
        )

        # 3. Build delimited, sanitized context
        context = self.context_builder.build(
            bundle=bundle,
            user_facts=user_facts,
            additional_evidence=additional_evidence,
        )

        # 4. Build prompt messages
        messages = self.prompt_builder.build(
            task_type=effective_task,
            context=context,
            user_query=query,
        )

        # 5. Call LLM provider
        raw_output = self.llm_provider.generate(
            messages=messages,
            temperature=self.config.temperature,
        )

        # 6. Validate grounding and construct canonical response
        validated_response = self.validator.validate_and_ground(
            raw_response=raw_output,
            task_type=effective_task,
            context=context,
        )

        # Attach evidence context for Phase 7 safety and citation auditing
        validated_response.structured_data["_evidence_context"] = {
            k: v.model_dump() for k, v in context.evidence_map.items()
        }

        return validated_response

    def _prepare_evidence(
        self,
        query: str,
        document_text: Optional[str] = None,
        second_document_text: Optional[str] = None,
        filters: Optional[RetrievalFilters] = None,
        top_k: Optional[int] = None,
    ) -> tuple[EvidenceBundle, List[RetrievedEvidence]]:
        """
        Retrieve evidence from KB and/or create temporary evidence blocks from user documents.
        """
        additional_evidence: List[RetrievedEvidence] = []

        if document_text:
            additional_evidence.append(
                RetrievedEvidence(
                    rank=1,
                    chunk_id="USER_DOC_1",
                    kb_chunk_id="KB_USER_DOC_1",
                    document_id="USER_DOCUMENT_A",
                    title="User Provided Document A",
                    section="Main",
                    text=document_text,
                    source_authority="USER_DOCUMENT",
                    synthetic=True,
                )
            )

        if second_document_text:
            additional_evidence.append(
                RetrievedEvidence(
                    rank=2,
                    chunk_id="USER_DOC_2",
                    kb_chunk_id="KB_USER_DOC_2",
                    document_id="USER_DOCUMENT_B",
                    title="User Provided Document B",
                    section="Main",
                    text=second_document_text,
                    source_authority="USER_DOCUMENT",
                    synthetic=True,
                )
            )

        # If user provided a specific document and no query, use doc snippet as query for any needed background
        search_query = query.strip()
        if not search_query and document_text:
            search_query = document_text[:200]

        if search_query:
            try:
                bundle = self.retriever.retrieve(
                    query=search_query,
                    top_k=top_k or 5,
                    filters=filters,
                )
            except Exception:
                # Fallback to empty bundle if retrieval fails or DB empty
                bundle = EvidenceBundle(
                    query=search_query,
                    normalized_query=search_query.lower(),
                    results=[],
                )
        else:
            bundle = EvidenceBundle(
                query="",
                normalized_query="",
                results=[],
            )

        return bundle, additional_evidence

    # ──────────────────────────────────────────────
    # Specialized Feature APIs
    # ──────────────────────────────────────────────

    def answer(
        self,
        query: str,
        user_facts: Optional[List[UserFact]] = None,
        filters: Optional[RetrievalFilters] = None,
        top_k: int = 5,
    ) -> LegalAIResponse:
        """Feature 1: Grounded Legal Q&A."""
        return self.execute_task(
            query=query,
            task_type=TaskType.LEGAL_QA,
            user_facts=user_facts,
            filters=filters,
            top_k=top_k,
        )

    def summarize(
        self,
        document_text: str,
        query: str = "Summarize this legal document",
        filters: Optional[RetrievalFilters] = None,
    ) -> LegalAIResponse:
        """Feature 2: Legal Document Summarization."""
        return self.execute_task(
            query=query,
            task_type=TaskType.SUMMARY,
            document_text=document_text,
            filters=filters,
        )

    def simplify(
        self,
        text: str,
        query: str = "Explain and simplify this legal text in plain English",
    ) -> LegalAIResponse:
        """Feature 10: Document Explanation / Plain-Language Simplification."""
        return self.execute_task(
            query=query,
            task_type=TaskType.SIMPLIFY,
            document_text=text,
        )

    def analyze_clause(
        self,
        clause_text: str,
        query: str = "Analyze this legal clause for obligations, rights, and risks",
    ) -> LegalAIResponse:
        """Feature 3: Clause / Provision Analysis."""
        return self.execute_task(
            query=query,
            task_type=TaskType.CLAUSE_ANALYSIS,
            document_text=clause_text,
        )

    def compare(
        self,
        doc_a_text: str,
        doc_b_text: str,
        query: str = "Compare these two contract versions and identify differences",
    ) -> LegalAIResponse:
        """Feature 4: Contract / Document Comparison."""
        return self.execute_task(
            query=query,
            task_type=TaskType.COMPARE_DOCUMENTS,
            document_text=doc_a_text,
            second_document_text=doc_b_text,
        )

    def extract_obligations(
        self,
        text: str,
        query: str = "Extract all mandatory legal obligations from this document",
    ) -> LegalAIResponse:
        """Feature 5: Obligation Extraction."""
        return self.execute_task(
            query=query,
            task_type=TaskType.EXTRACT_OBLIGATIONS,
            document_text=text,
        )

    def extract_deadlines(
        self,
        text: str,
        query: str = "Extract all deadlines, timelines, and date requirements",
    ) -> LegalAIResponse:
        """Feature 6: Deadline / Date Extraction."""
        return self.execute_task(
            query=query,
            task_type=TaskType.EXTRACT_DEADLINES,
            document_text=text,
        )

    def extract_rights_duties(
        self,
        text: str,
        query: str = "Extract all legal rights, duties, permissions, and prohibitions",
    ) -> LegalAIResponse:
        """Feature 7: Rights / Duties Extraction."""
        return self.execute_task(
            query=query,
            task_type=TaskType.EXTRACT_RIGHTS_DUTIES,
            document_text=text,
        )

    def identify_issues(
        self,
        text: str,
        query: str = "Identify legal issues, ambiguities, or compliance risks",
    ) -> LegalAIResponse:
        """Feature 8: Legal Issue Identification."""
        return self.execute_task(
            query=query,
            task_type=TaskType.IDENTIFY_ISSUES,
            document_text=text,
        )

    def generate_next_steps(
        self,
        query: str,
        document_text: Optional[str] = None,
    ) -> LegalAIResponse:
        """Feature 9: Evidence-Based Next Steps."""
        return self.execute_task(
            query=query,
            task_type=TaskType.NEXT_STEPS,
            document_text=document_text,
        )

    def generate_checklist(
        self,
        query: str,
        document_text: Optional[str] = None,
    ) -> LegalAIResponse:
        """Feature 11: Structured Legal Checklists."""
        return self.execute_task(
            query=query,
            task_type=TaskType.CHECKLIST,
            document_text=document_text,
        )

    def multi_doc_reasoning(
        self,
        query: str,
        filters: Optional[RetrievalFilters] = None,
    ) -> LegalAIResponse:
        """Feature 12: Multi-Document Reasoning across statutes and judgments."""
        return self.execute_task(
            query=query,
            task_type=TaskType.MULTI_DOCUMENT_ANALYSIS,
            filters=filters,
            top_k=8,
        )
