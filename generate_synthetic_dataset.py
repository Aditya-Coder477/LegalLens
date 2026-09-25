"""
generate_synthetic_dataset.py
==============================
CLI entry point to generate the complete LegalLens Synthetic Indian Legal Corpus.

Usage:
    python generate_synthetic_dataset.py [--output-dir legal-data/synthetic] [--seed 20260925]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline.synthetic import GENERATOR_VERSION, LEGAL_DISCLAIMER, SEED
from pipeline.synthetic.engine import SyntheticCorpusEngine

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic legal corpus for LegalLens testing and evaluation."
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="legal-data/synthetic",
        help="Target output directory for the synthetic dataset.",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=SEED,
        help="Random seed for deterministic generation.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("LegalLens -- Synthetic Indian Legal Corpus Generator")
    print(f"Version: {GENERATOR_VERSION} | Seed: {args.seed}")
    print("=" * 70)
    print(f"DISCLAIMER:\n{LEGAL_DISCLAIMER}\n")
    print(f"Target Output Directory: {args.output_dir}\n")

    engine = SyntheticCorpusEngine(output_root=args.output_dir)
    print("Generating synthetic Acts, Rules, Notifications, Guidance, Judgments, and Contracts...")
    stats = engine.generate_all()

    print("\nGeneration Completed Successfully!")
    print(f"- Total Documents: {stats['total_documents']}")
    print(f"- Total Sections: {stats['total_sections']}")
    print(f"- Total Simulated Pages: {stats['total_pages']}")
    print(f"- Duration: {stats['duration_seconds']:.2f} seconds")
    print("\nDocuments by Type:")
    for doc_type, count in stats["documents_by_type"].items():
        print(f"  * {doc_type}: {count}")

    print("\nEvaluation Benchmarks:")
    for bench_name, count in stats["evaluation_benchmarks"].items():
        print(f"  * {bench_name}: {count}")

    print("\nAll files, metadata, and manifest written to:", Path(args.output_dir).resolve())
    print("=" * 70)

if __name__ == "__main__":
    main()
