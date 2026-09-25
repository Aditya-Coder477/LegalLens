"""
pipeline/retrieval/retriever.py
===============================
Master Hybrid Retrieval Service Facade for LegalLens.
Orchestrates Query Processing, Lexical Search, Semantic Search,
Rank Fusion, Deduplication, Context Expansion, Reranking, and Evidence Packaging.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from pipeline.knowledge_base.config import get_kb_config
from pipeline.knowledge_base.db import DatabaseManager
from pipeline.knowledge_base.providers import EmbeddingProvider, get_embedding_provider

from .config import RetrievalConfig, get_retrieval_config
from .context_expander import ContextExpander
from .deduplication import CandidateDeduplicator
from .evidence import EvidenceBuilder
from .fusion import FusionEngine
from .lexical_retriever import LexicalRetriever
from .models import EvidenceBundle, RetrievalFilters
from .query_processor import QueryProcessor
from .reranker import LocalTermReranker, NoOpReranker, Reranker
from .semantic_retriever import SemanticRetriever


class HybridRetriever:
    """
    Main retrieval engine combining Lexical (BM25/FTS) and Semantic (pgvector / dense)
    candidate generation with Reciprocal Rank Fusion.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        config: Optional[RetrievalConfig] = None,
        reranker: Optional[Reranker] = None,
    ):
        kb_cfg = get_kb_config()
        self.config = config or get_retrieval_config()
        self.db = db_manager or DatabaseManager(kb_cfg.database_url)
        self.provider = embedding_provider or get_embedding_provider(
            provider_name=kb_cfg.embedding_provider,
            model_name=kb_cfg.embedding_model,
            dimension=kb_cfg.embedding_dimension,
            api_key=kb_cfg.openai_api_key,
            base_url=kb_cfg.openai_base_url,
            normalize=kb_cfg.normalize_embeddings,
        )

        # Components
        self.query_processor = QueryProcessor()
        self.lexical_retriever = LexicalRetriever(self.db)
        self.semantic_retriever = SemanticRetriever(
            self.db,
            self.provider,
            query_cache_enabled=self.config.query_cache_enabled,
        )
        self.fusion_engine = FusionEngine(rrf_k=self.config.rrf_k)
        self.deduplicator = CandidateDeduplicator()
        self.context_expander = ContextExpander(
            self.db,
            max_parents=self.config.max_parent_context,
            max_cross_refs=self.config.max_cross_reference_hops,
            max_definitions=self.config.max_definition_expansions,
        )
        self.reranker = reranker or (
            LocalTermReranker() if self.config.reranker_enabled else NoOpReranker()
        )
        self.evidence_builder = EvidenceBuilder(self.config)

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        lexical_top_k: Optional[int] = None,
        semantic_top_k: Optional[int] = None,
        filters: Optional[RetrievalFilters] = None,
        rerank: Optional[bool] = None,
        debug: bool = False,
    ) -> EvidenceBundle:
        """
        Execute full end-to-end hybrid retrieval workflow.
        """
        t0 = time.time()
        final_top_k = top_k or self.config.final_top_k
        lex_k = lexical_top_k or self.config.lexical_top_k
        sem_k = semantic_top_k or self.config.semantic_top_k

        # 1. Query Processing
        t_qp_0 = time.time()
        normalized_q = self.query_processor.normalize(query)
        q_type = self.query_processor.detect_query_type(query)
        extracted_entities = self.query_processor.extract_legal_entities(query)
        t_qp = time.time() - t_qp_0

        # 2. Lexical Candidate Retrieval
        t_lex_0 = time.time()
        lexical_candidates = self.lexical_retriever.retrieve(
            query=query,
            top_k=lex_k,
            filters=filters,
        )
        t_lex = time.time() - t_lex_0

        # 3. Semantic Candidate Retrieval
        t_sem_0 = time.time()
        semantic_candidates = self.semantic_retriever.retrieve(
            query=query,
            top_k=sem_k,
            filters=filters,
        )
        t_sem = time.time() - t_sem_0

        # 4. Hybrid Rank Fusion (RRF)
        t_fus_0 = time.time()
        fused_candidates = self.fusion_engine.fuse(
            lexical_candidates=lexical_candidates,
            semantic_candidates=semantic_candidates,
            top_k=max(final_top_k * 3, 20),
        )
        t_fus = time.time() - t_fus_0

        # 5. Candidate Deduplication
        deduped_candidates = self.deduplicator.deduplicate(fused_candidates)

        # 6. Context Expansion (parents, definitions, cross-references)
        t_ctx_0 = time.time()
        supporting_ctx = self.context_expander.expand(deduped_candidates[:5])
        t_ctx = time.time() - t_ctx_0

        # 7. Optional Reranking
        t_rerank_0 = time.time()
        should_rerank = rerank if rerank is not None else self.config.reranker_enabled
        if should_rerank:
            reranker = LocalTermReranker()
            ranked_candidates = reranker.rerank(query, deduped_candidates[: self.config.reranker_top_n])
        else:
            ranked_candidates = deduped_candidates
        t_rerank = time.time() - t_rerank_0

        # 8. Evidence Selection & Packaging
        debug_dict = None
        if debug:
            debug_dict = {
                "query": query,
                "normalized_query": normalized_q,
                "query_type": q_type.value,
                "extracted_entities": extracted_entities,
                "lexical_candidate_count": len(lexical_candidates),
                "semantic_candidate_count": len(semantic_candidates),
                "fused_candidate_count": len(fused_candidates),
                "deduped_candidate_count": len(deduped_candidates),
                "parent_contexts_expanded": len(supporting_ctx.parent_chunks),
                "definitions_expanded": len(supporting_ctx.definitions),
                "cross_references_expanded": len(supporting_ctx.cross_references),
                "reranker_active": should_rerank,
                "latencies_ms": {
                    "query_processing": round(t_qp * 1000, 2),
                    "lexical_retrieval": round(t_lex * 1000, 2),
                    "semantic_retrieval": round(t_sem * 1000, 2),
                    "rank_fusion": round(t_fus * 1000, 2),
                    "context_expansion": round(t_ctx * 1000, 2),
                    "reranking": round(t_rerank * 1000, 2),
                    "total": round((time.time() - t0) * 1000, 2),
                },
            }

        bundle = self.evidence_builder.build_bundle(
            query=query,
            normalized_query=normalized_q,
            query_type=q_type,
            candidates=ranked_candidates[:final_top_k],
            supporting_context=supporting_ctx,
            filters=filters,
            debug_info=debug_dict,
        )

        return bundle
