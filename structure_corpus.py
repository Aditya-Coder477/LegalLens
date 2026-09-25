#!/usr/bin/env python3
"""
structure_corpus.py
====================
CLI for Phase 3: Legal Document Structuring & Provenance-Preserving Chunking.

Usage:
    python structure_corpus.py [OPTIONS]

Options:
    --input PATH          Path to synthetic corpus root [default: legal-data/synthetic]
    --output PATH         Path for structured output [default: <input>/structured]
    --limit N             Process only first N documents
    --document-type TYPE  Filter by document type (act, rule, judgment, contract, ...)
    --validate            Run validator after structuring
    --stats               Print statistics to stdout
    --resume              Resume from previous run (skip already-processed docs) [default: True]
    --overwrite           Overwrite previous output (disables resume)
    --target-tokens N     Target tokens per chunk [default: 600]
    --max-tokens N        Maximum tokens per chunk [default: 900]
    --min-tokens N        Minimum tokens per chunk [default: 100]
    --quiet               Suppress verbose logging
    -h, --help            Show this help message

Examples:
    python structure_corpus.py
    python structure_corpus.py --limit 10
    python structure_corpus.py --document-type act --overwrite
    python structure_corpus.py --validate --stats
    python structure_corpus.py --resume  # Continue after interruption
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LegalLens Phase 3: Structure & chunk the synthetic legal corpus.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("legal-data/synthetic"),
        help="Path to synthetic corpus root (default: legal-data/synthetic)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for structured data (default: <input>/structured)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only first N documents",
    )
    parser.add_argument(
        "--document-type",
        type=str,
        default=None,
        dest="document_type",
        choices=["act", "amendment", "rule", "notification", "circular",
                 "guideline", "judgment", "contract"],
        help="Filter to a specific document type",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help="Run validate_structured_corpus.py after structuring",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        default=False,
        help="Print statistics to stdout after run",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from previous run (default: True)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite previous output (disables resume)",
    )
    parser.add_argument(
        "--target-tokens",
        type=int,
        default=600,
        dest="target_tokens",
        help="Target tokens per chunk (default: 600)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=900,
        dest="max_tokens",
        help="Maximum tokens per chunk (default: 900)",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=100,
        dest="min_tokens",
        help="Minimum tokens per chunk (default: 100)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress verbose logging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Validate input path
    synthetic_root = args.input.resolve()
    if not synthetic_root.exists():
        print(f"ERROR: Input path does not exist: {synthetic_root}", file=sys.stderr)
        return 1

    # Determine output path
    output_root = args.output.resolve() if args.output else (synthetic_root / "structured")

    print("=" * 60)
    print("LegalLens — Phase 3: Legal Document Structuring & Chunking")
    print("=" * 60)
    print(f"Input         : {synthetic_root}")
    print(f"Output        : {output_root}")
    print(f"Document type : {args.document_type or 'all'}")
    print(f"Limit         : {args.limit or 'none'}")
    print(f"Target tokens : {args.target_tokens}")
    print(f"Max tokens    : {args.max_tokens}")
    print(f"Min tokens    : {args.min_tokens}")
    print(f"Resume        : {not args.overwrite}")
    print(f"Overwrite     : {args.overwrite}")
    print()

    # Import and run engine
    try:
        from pipeline.structuring.engine import StructuringEngine
    except ImportError as e:
        print(f"ERROR: Cannot import structuring engine: {e}", file=sys.stderr)
        print("Make sure pipeline/structuring/ is on PYTHONPATH.", file=sys.stderr)
        return 1

    engine = StructuringEngine(
        synthetic_root       = synthetic_root,
        output_root          = output_root,
        target_tokens        = args.target_tokens,
        max_tokens           = args.max_tokens,
        min_tokens           = args.min_tokens,
        overlap_tokens       = 50,
        document_type_filter = args.document_type,
        limit                = args.limit,
        overwrite            = args.overwrite,
        resume               = not args.overwrite,
        verbose              = not args.quiet,
    )

    summary = engine.run()

    if "error" in summary:
        print(f"ERROR: {summary['error']}", file=sys.stderr)
        return 1

    if args.stats:
        import json
        print("\n--- Statistics ---")
        print(json.dumps(summary, indent=2, default=str))

    if args.validate:
        print("\nRunning validator...")
        result = subprocess.run(
            [sys.executable, "validate_structured_corpus.py", "--input", str(output_root)],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"\nERROR: Validation FAILED (exit code {result.returncode})", file=sys.stderr)
            return result.returncode
        else:
            print("Validation PASSED.")

    return 0 if not summary.get("documents_errored") else 2


if __name__ == "__main__":
    sys.exit(main())
