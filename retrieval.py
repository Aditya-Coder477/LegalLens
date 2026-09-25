#!/usr/bin/env python3
"""
retrieval.py
============
CLI interface for LegalLens Phase 5: Hybrid RAG + Retrieval.

Subcommands:
    search      Execute hybrid (lexical + semantic) retrieval for a query
    benchmark   Benchmark and compare retrieval strategies on ground-truth datasets
    health      Verify Knowledge Base connectivity, vector index, and provider health
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline.knowledge_base.config import get_kb_config
from pipeline.knowledge_base.db import DatabaseManager
from pipeline.retrieval.config import get_retrieval_config
from pipeline.retrieval.evaluation import RetrievalEvaluator
from pipeline.retrieval.models import RetrievalFilters
from pipeline.retrieval.retriever import HybridRetriever


def cmd_search(args: argparse.Namespace) -> int:
    query = args.query
    if not query or not query.strip():
        print("ERROR: --query cannot be empty", file=sys.stderr)
        return 1

    retriever = HybridRetriever()

    filters = RetrievalFilters(
        document_type=args.document_type,
        source_authority=args.source_authority,
        legal_domain=args.legal_domain,
        document_id=args.document_id,
        version_id=args.version_id,
        synthetic=args.synthetic,
    )

    bundle = retriever.retrieve(
        query=query,
        top_k=args.top_k,
        lexical_top_k=args.lexical_top_k,
        semantic_top_k=args.semantic_top_k,
        filters=filters,
        rerank=args.rerank,
        debug=args.debug,
    )

    if args.json:
        print(bundle.model_dump_json(indent=2))
        return 0

    print("=" * 70)
    print("LEGALLENS HYBRID RETRIEVAL — EVIDENCE BUNDLE")
    print("=" * 70)
    print(f"Query            : \"{bundle.query}\"")
    print(f"Normalized Query : \"{bundle.normalized_query}\"")
    print(f"Query Intent     : {bundle.query_type.value}")
    print(f"Retrieval Status : {bundle.retrieval_status.value}")
    print(f"Results Found    : {len(bundle.results)}")
    print(f"Timestamp        : {bundle.retrieval_timestamp}")

    if bundle.debug_info:
        dbg = bundle.debug_info
        print("-" * 70)
        print("DEBUG TRACE:")
        print(f"  Extracted Entities : {dbg['extracted_entities']}")
        print(f"  Candidate Counts   : Lexical={dbg['lexical_candidate_count']}, Semantic={dbg['semantic_candidate_count']}, Fused={dbg['fused_candidate_count']}")
        print(f"  Supporting Context : Parents={dbg['parent_contexts_expanded']}, Defs={dbg['definitions_expanded']}, XRefs={dbg['cross_references_expanded']}")
        print(f"  Latencies (ms)     : Lex={dbg['latencies_ms']['lexical_retrieval']}ms, Sem={dbg['latencies_ms']['semantic_retrieval']}ms, Total={dbg['latencies_ms']['total']}ms")

    print("-" * 70)
    for ev in bundle.results:
        print(f"#{ev.rank} [{ev.fusion_score:.5f} RRF] {ev.document_id} | Section {ev.section or 'N/A'}: {ev.title or 'N/A'}")
        print(f"    Chunk ID   : {ev.chunk_id} (Type: {ev.chunk_type})")
        print(f"    Methods    : {', '.join(ev.retrieval_methods)} (Lex: {ev.lexical_score or 0.0:.2f}, Sem: {ev.semantic_score or 0.0:.4f})")
        print(f"    Provenance : Authority={ev.source_authority} | Synthetic={ev.synthetic} | ProvID={ev.provenance_id}")
        preview = (ev.text[:200] + "...") if len(ev.text) > 200 else ev.text
        print(f"    Text       : {preview}")
        print()

    # Supporting Context
    sc = bundle.supporting_context
    if sc.parent_chunks or sc.definitions or sc.cross_references:
        print("-" * 70)
        print("SUPPORTING CONTEXT EXPANSIONS:")
        for p in sc.parent_chunks:
            print(f"  [Parent] {p['document_id']} Section {p['section']}: {p['title']}")
        for d in sc.definitions:
            print(f"  [Definition] '{d['term']}': {d['definition_text'][:120]}...")
        for r in sc.cross_references:
            print(f"  [Cross-Reference] {r['source_document_id']} -> '{r['target_reference']}'")

    print("=" * 70)
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    retriever = HybridRetriever()
    evaluator = RetrievalEvaluator(retriever, output_dir=Path(args.output_dir))

    print("=" * 70)
    print("LEGALLENS RETRIEVAL BENCHMARK — STRATEGY COMPARISON")
    print("=" * 70)
    print(f"Dataset : {dataset_path}")
    print("Running benchmark across Lexical, Semantic, Hybrid RRF, and Hybrid + Reranker...")
    print()

    bench = evaluator.benchmark_all_strategies(dataset_path)

    print(f"{'Strategy':<16} {'Recall@1':<10} {'Recall@5':<10} {'Recall@10':<10} {'MRR':<10} {'HitRate@5':<12} {'Latency':<10}")
    print("-" * 78)
    for strat, m in bench["strategies"].items():
        print(f"{strat:<16} {m['recall_at_1']:<10.4f} {m['recall_at_5']:<10.4f} {m['recall_at_10']:<10.4f} {m['mrr']:<10.4f} {m['hit_rate_at_5']:<12.4f} {m['latency_ms']['avg']}ms")

    print("=" * 70)
    print(f"Reports written to : {evaluator.reports_dir}")
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    cfg = get_kb_config()
    db = DatabaseManager(cfg.database_url)
    diag = db.check_connectivity()
    pgv = db.check_pgvector()

    print("=" * 60)
    print("LegalLens Retrieval — System Health & Index Readiness")
    print("=" * 60)
    print(f"Database Connection : {'CONNECTED' if diag['connected'] else 'FAILED'}")
    print(f"Database Dialect    : {diag['dialect']}")
    print(f"Target URL          : {diag['url']}")
    print(f"pgvector Available  : {pgv.get('available')}")
    print(f"pgvector Installed  : {pgv.get('installed')}")
    print(f"Embedding Provider  : {cfg.embedding_provider} ({cfg.embedding_model}, {cfg.embedding_dimension}d)")

    if diag["connected"]:
        with db.session_scope() as s:
            from pipeline.knowledge_base.db_models import EmbeddingTable, KBChunkTable
            chunks_cnt = s.query(KBChunkTable).count()
            embs_cnt = s.query(EmbeddingTable).count()
            print(f"Total Chunks        : {chunks_cnt}")
            print(f"Total Vectors       : {embs_cnt}")
            status = "HEALTHY" if chunks_cnt > 0 and embs_cnt > 0 else "EMPTY_KB"
    else:
        status = "DATABASE_UNAVAILABLE"

    print(f"Overall Status      : {status}")
    print("=" * 60)
    return 0 if status == "HEALTHY" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LegalLens Phase 5: Hybrid RAG + Retrieval CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # search
    p_search = subparsers.add_parser("search", help="Execute hybrid legal retrieval for a query")
    p_search.add_argument("--query", type=str, required=True, help="User legal question or provision citation")
    p_search.add_argument("--top-k", type=int, default=8, help="Number of evidence chunks to return")
    p_search.add_argument("--lexical-top-k", type=int, default=50, help="Lexical candidates limit")
    p_search.add_argument("--semantic-top-k", type=int, default=50, help="Semantic candidates limit")
    p_search.add_argument("--document-type", type=str, default=None, help="Filter by document type (ACT, RULE, etc.)")
    p_search.add_argument("--source-authority", type=str, default=None, help="Filter by source authority")
    p_search.add_argument("--document-id", type=str, default=None, help="Filter by specific document ID")
    p_search.add_argument("--version-id", type=str, default=None, help="Filter by version label")
    p_search.add_argument("--legal-domain", type=str, default=None, help="Filter by legal domain")
    p_search.add_argument("--synthetic", type=bool, default=None, help="Filter by synthetic flag")
    p_search.add_argument("--rerank", action="store_true", default=None, help="Enable post-fusion reranking")
    p_search.add_argument("--debug", action="store_true", default=False, help="Display verbose query & pipeline debug trace")
    p_search.add_argument("--json", action="store_true", default=False, help="Output evidence bundle as JSON")

    # benchmark
    p_bench = subparsers.add_parser("benchmark", help="Benchmark retrieval strategies against ground truth")
    p_bench.add_argument("--dataset", type=str, default="legal-data/synthetic/evaluation/retrieval_ground_truth.jsonl", help="Ground truth JSONL dataset path")
    p_bench.add_argument("--output-dir", type=str, default="legal-data/knowledge_base", help="Output directory for reports")

    # health
    p_health = subparsers.add_parser("health", help="Check Knowledge Base connectivity and index readiness")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "search": cmd_search,
        "benchmark": cmd_benchmark,
        "health": cmd_health,
    }

    handler = dispatch.get(args.subcommand)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
