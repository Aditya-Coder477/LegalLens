#!/usr/bin/env python3
"""
knowledge_base.py
=================
CLI interface for LegalLens Phase 4: Knowledge Base + Embeddings.

Subcommands:
    init-db         Initialize database schema, verify extensions, create tables
    validate-input  Validate Phase 3 structured chunks schema prior to ingestion
    ingest          Ingest chunks, generate/reuse embeddings, store in KB & database
    validate        Comprehensive validation of canonical KB records and vectors
    stats           Display current Knowledge Base and embedding statistics
    smoke-search    Run vector similarity smoke test on knowledge base index
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from pipeline.knowledge_base.config import get_kb_config
from pipeline.knowledge_base.db import DatabaseManager
from pipeline.knowledge_base.engine import KnowledgeBaseEngine
from pipeline.knowledge_base.models import KBQualityReport
from pipeline.knowledge_base.providers import get_embedding_provider
from pipeline.knowledge_base.validator import InputChunkValidator, KnowledgeBaseValidator


def cmd_init_db(args: argparse.Namespace) -> int:
    cfg = get_kb_config()
    db = DatabaseManager(args.db_url or cfg.database_url)
    res = db.init_db()

    print("=" * 60)
    print("LegalLens Knowledge Base — Database Initialization")
    print("=" * 60)
    print(f"Status           : {res.get('status')}")
    print(f"Dialect          : {res.get('dialect')}")
    print(f"Database Target  : {res.get('url')}")
    print(f"pgvector Status  : {res.get('pgvector')}")
    print(f"Tables Created   : {', '.join(res.get('tables_created', []))}")
    print("=" * 60)
    return 0 if res.get("status") == "success" else 1


def cmd_validate_input(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    validator = InputChunkValidator(input_path)
    is_valid, issues, stats = validator.validate()

    print("=" * 60)
    print("LegalLens Knowledge Base — Input Chunks Validation")
    print("=" * 60)
    print(f"Input file       : {input_path}")
    print(f"Total records    : {stats['total_records']}")
    print(f"Valid records    : {stats['valid_records']}")
    print(f"Total issues     : {len(issues)}")
    print()

    for iss in issues[:20]:
        print(f"  {iss}")
    if len(issues) > 20:
        print(f"  ... and {len(issues) - 20} more issues")

    print()
    if is_valid:
        print("STATUS: INPUT VALIDATION PASSED")
        return 0
    else:
        print("STATUS: INPUT VALIDATION FAILED")
        return 1


def cmd_ingest(args: argparse.Namespace) -> int:
    cfg = get_kb_config()
    provider = get_embedding_provider(
        provider_name=args.provider or cfg.embedding_provider,
        model_name=args.model or cfg.embedding_model,
        dimension=cfg.embedding_dimension,
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        normalize=cfg.normalize_embeddings,
    )

    engine = KnowledgeBaseEngine(
        chunks_path=Path(args.input) if args.input else cfg.structured_chunks_path,
        kb_data_path=Path(args.kb_path) if args.kb_path else cfg.kb_data_path,
        db_url=args.db_url or cfg.database_url,
        provider=provider,
        batch_size=args.batch_size or cfg.embedding_batch_size,
        limit=args.limit,
        document_type_filter=args.document_type,
        source_authority_filter=args.source_authority,
        resume=args.resume and not args.overwrite,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        verbose=True,
    )

    summary = engine.ingest()
    return 0 if summary.get("failed_embeddings", 0) == 0 else 1


def cmd_validate(args: argparse.Namespace) -> int:
    cfg = get_kb_config()
    db = DatabaseManager(args.db_url or cfg.database_url)
    validator = KnowledgeBaseValidator(db, expected_dimension=cfg.embedding_dimension)
    is_valid, issues, stats = validator.validate()

    print("=" * 60)
    print("LegalLens Knowledge Base — System Integrity Validation")
    print("=" * 60)
    print(f"Total KB Chunks  : {stats['total_chunks']}")
    print(f"Total Embeddings : {stats['total_embeddings']}")
    print(f"Embedded Chunks  : {stats['embedded_chunks']}")
    print(f"Orphan Chunks    : {stats['orphan_chunks']}")
    print(f"Orphan Vectors   : {stats['orphan_embeddings']}")
    print(f"Total Issues     : {len(issues)}")
    print()

    criticals = [iss for iss in issues if iss.severity == "CRITICAL"]
    warnings = [iss for iss in issues if iss.severity == "WARNING"]

    for iss in criticals:
        print(f"  {iss}")
    for iss in warnings[:15]:
        print(f"  {iss}")
    if len(warnings) > 15:
        print(f"  ... and {len(warnings) - 15} more warnings")

    print()
    if is_valid:
        print("STATUS: KNOWLEDGE BASE VALIDATION PASSED")
        return 0
    else:
        print(f"STATUS: KNOWLEDGE BASE VALIDATION FAILED ({len(criticals)} critical issues)")
        return 1


def cmd_stats(args: argparse.Namespace) -> int:
    cfg = get_kb_config()
    stats_file = cfg.kb_data_path / "embeddings" / "embedding_stats.json"
    quality_file = cfg.kb_data_path / "reports" / "kb_quality_report.json"
    manifest_file = cfg.kb_data_path / "manifests" / "knowledge_base_manifest.json"

    print("=" * 60)
    print("LegalLens Knowledge Base — Statistics")
    print("=" * 60)

    if quality_file.exists():
        q = json.loads(quality_file.read_text(encoding="utf-8"))
        print(f"Documents          : {q.get('documents')}")
        print(f"Versions           : {q.get('versions')}")
        print(f"Legal Units        : {q.get('legal_units')}")
        print(f"Total Chunks       : {q.get('chunks')}")
        print(f"Embedded Chunks    : {q.get('embedded_chunks')}")
        print(f"Coverage           : {q.get('embedding_coverage', 0) * 100:.2f}%")
        print(f"Synthetic Chunks   : {q.get('synthetic_chunks')}")
        print(f"Tokens (min/avg/max): {q.get('min_tokens')} / {q.get('average_tokens')} / {q.get('max_tokens')}")
    else:
        print("Knowledge base quality report not found. Run ingest first.")

    if stats_file.exists():
        s = json.loads(stats_file.read_text(encoding="utf-8"))
        print(f"New Embeddings     : {s.get('new')}")
        print(f"Reused Embeddings  : {s.get('reused')}")
        print(f"Failed Embeddings  : {s.get('failed')}")
        print(f"Provider / Model   : {s.get('provider')} / {s.get('model')} ({s.get('dimension')}d)")

    print("=" * 60)
    return 0


def cmd_smoke_search(args: argparse.Namespace) -> int:
    query = args.query
    if not query or not query.strip():
        print("ERROR: --query cannot be empty", file=sys.stderr)
        return 1

    cfg = get_kb_config()
    db = DatabaseManager(args.db_url or cfg.database_url)
    provider = get_embedding_provider(
        provider_name=cfg.embedding_provider,
        model_name=cfg.embedding_model,
        dimension=cfg.embedding_dimension,
        normalize=cfg.normalize_embeddings,
    )

    query_vec = provider.embed_text(query)
    results = db.search_similar_chunks(query_vec, top_k=args.top_k)

    print("=" * 70)
    print("VECTOR INDEX SMOKE TEST — NOT PRODUCTION RETRIEVAL")
    print("=" * 70)
    print(f"Query: \"{query}\"")
    print(f"Model: {provider.provider_name}:{provider.model_name} ({provider.dimension}d)")
    print(f"Results retrieved: {len(results)}")
    print("-" * 70)

    for i, r in enumerate(results, 1):
        print(f"#{i} [Similarity: {r['similarity']:.4f}] {r['document_id']} | Section {r.get('section', 'N/A')}")
        print(f"    Chunk ID : {r['chunk_id']}")
        print(f"    Title    : {r.get('title')}")
        print(f"    Preview  : {r['text_preview']}")
        print(f"    Authority: {r['source_authority']} (Synthetic={r['synthetic']})")
        print()

    print("=" * 70)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LegalLens Phase 4: Knowledge Base + Embeddings Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # init-db
    p_init = subparsers.add_parser("init-db", help="Initialize database and verify schema/pgvector")
    p_init.add_argument("--db-url", type=str, default=None, help="Database connection URL")

    # validate-input
    p_vin = subparsers.add_parser("validate-input", help="Validate structured chunks input file")
    p_vin.add_argument("--input", type=str, default="legal-data/synthetic/structured/chunks.jsonl", help="Input chunks path")

    # ingest
    p_ing = subparsers.add_parser("ingest", help="Ingest chunks and generate embeddings into KB")
    p_ing.add_argument("--input", type=str, default=None, help="Input chunks.jsonl file")
    p_ing.add_argument("--kb-path", type=str, default=None, help="Knowledge base output directory")
    p_ing.add_argument("--db-url", type=str, default=None, help="Database connection URL")
    p_ing.add_argument("--limit", type=int, default=None, help="Limit number of chunks to ingest")
    p_ing.add_argument("--document-type", type=str, default=None, help="Filter by document type")
    p_ing.add_argument("--source-authority", type=str, default=None, help="Filter by source authority")
    p_ing.add_argument("--batch-size", type=int, default=None, help="Batch size for embedding generation")
    p_ing.add_argument("--provider", type=str, default=None, choices=["local", "fake", "openai"], help="Embedding provider")
    p_ing.add_argument("--model", type=str, default=None, help="Embedding model name")
    p_ing.add_argument("--resume", action="store_true", default=True, help="Resume previous ingestion run")
    p_ing.add_argument("--overwrite", action="store_true", default=False, help="Overwrite previous ingestion")
    p_ing.add_argument("--dry-run", action="store_true", default=False, help="Perform dry run without writing")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate knowledge base integrity and embeddings")
    p_val.add_argument("--db-url", type=str, default=None, help="Database connection URL")

    # stats
    p_stat = subparsers.add_parser("stats", help="Display Knowledge Base statistics")

    # smoke-search
    p_srch = subparsers.add_parser("smoke-search", help="Run vector similarity smoke test")
    p_srch.add_argument("--query", type=str, required=True, help="Search query string")
    p_srch.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve")
    p_srch.add_argument("--db-url", type=str, default=None, help="Database connection URL")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "init-db": cmd_init_db,
        "validate-input": cmd_validate_input,
        "ingest": cmd_ingest,
        "validate": cmd_validate,
        "stats": cmd_stats,
        "smoke-search": cmd_smoke_search,
    }

    handler = dispatch.get(args.subcommand)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
