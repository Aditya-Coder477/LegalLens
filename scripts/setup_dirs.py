"""
scripts/setup_dirs.py
======================
Idempotent one-time setup script.
Creates the full legal-data/ directory tree and initialises empty CSV headers.

Usage:
    python scripts/setup_dirs.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.core.catalogue import SOURCES_CSV_FIELDS, FAILED_CSV_FIELDS, SKIPPED_CSV_FIELDS


DIRS = [
    # Raw source data
    "legal-data/raw/india_code/acts",
    "legal-data/raw/india_code/sections",
    "legal-data/raw/india_code/rules",
    "legal-data/raw/india_code/regulations",
    "legal-data/raw/india_code/notifications",
    "legal-data/raw/india_code/orders",
    "legal-data/raw/india_code/ordinances",
    "legal-data/raw/india_code/statutes",
    "legal-data/raw/india_code/circulars",
    "legal-data/raw/data_gov",
    "legal-data/raw/ecourts",
    "legal-data/raw/supreme_court",
    "legal-data/raw/nalsa",
    "legal-data/raw/legislative_department",
    "legal-data/raw/meity",
    # Processed
    "legal-data/processed/text",
    "legal-data/processed/pages",
    "legal-data/processed/sections",
    "legal-data/processed/clauses",
    "legal-data/processed/chunks",
    "legal-data/processed/metadata",
    # Datasets
    "legal-data/datasets",
    # Evaluation
    "legal-data/evaluation",
    # Logs
    "legal-data/logs",
]

CSV_INITS = {
    "legal-data/datasets/sources.csv": SOURCES_CSV_FIELDS,
    "legal-data/datasets/documents.csv": SOURCES_CSV_FIELDS,
    "legal-data/datasets/acts.csv": [
        "source_id", "title", "act_number", "act_year", "ministry",
        "legal_domain", "status", "official_url", "local_path", "sha256",
    ],
    "legal-data/datasets/sections.csv": [
        "section_id", "document_id", "act_id", "section_number",
        "sub_section", "heading", "source_url", "legal_domain",
        "page_start", "page_end",
    ],
    "legal-data/datasets/judgments.csv": [
        "source_id", "title", "court", "bench", "case_number",
        "judgment_date", "legal_domain", "official_url", "local_path", "sha256",
    ],
    "legal-data/datasets/datasets.csv": [
        "source_id", "title", "source_name", "resource_id", "format",
        "legal_domain", "official_url", "local_path", "sha256", "download_timestamp",
    ],
    "legal-data/logs/failed_downloads.csv": FAILED_CSV_FIELDS,
    "legal-data/logs/skipped_sources.csv": SKIPPED_CSV_FIELDS,
}

JSONL_INITS = [
    "legal-data/datasets/clauses.jsonl",
    "legal-data/evaluation/candidate_questions.jsonl",
    "legal-data/evaluation/comparison_cases.jsonl",
    "legal-data/evaluation/security_cases.jsonl",
]


def setup(root: Path = PROJECT_ROOT) -> None:
    print(f"Setting up legal-data/ directory structure in: {root}")

    # Create directories
    for d in DIRS:
        path = root / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {d}/")

    # Initialise CSV files with headers (only if they don't exist)
    for csv_path_str, fields in CSV_INITS.items():
        csv_path = root / csv_path_str
        if not csv_path.exists() or csv_path.stat().st_size == 0:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
            print(f"  [CREATED] {csv_path_str} (headers created)")
        else:
            print(f"  [SKIP] {csv_path_str} (already exists, skipping)")

    # Touch JSONL files
    for jsonl_path_str in JSONL_INITS:
        jsonl_path = root / jsonl_path_str
        if not jsonl_path.exists():
            jsonl_path.touch()
            print(f"  [CREATED] {jsonl_path_str}")

    # Initialise MANUAL_COLLECTION_TODO.md
    todo_path = root / "MANUAL_COLLECTION_TODO.md"
    if not todo_path.exists():
        todo_path.write_text(
            "# LegalLens — Manual Collection TODO\n\n"
            "Items that could not be collected automatically are listed below.\n"
            "Follow the instructions for each item to download and import manually.\n\n",
            encoding="utf-8",
        )
        print("  [CREATED] MANUAL_COLLECTION_TODO.md")

    # Initialise COLLECTION_REPORT.md
    report_path = root / "COLLECTION_REPORT.md"
    if not report_path.exists():
        report_path.write_text(
            "# LegalLens — Collection Report\n\n"
            "_Run `python generate_report.py` to regenerate this report._\n",
            encoding="utf-8",
        )
        print("  [CREATED] COLLECTION_REPORT.md")

    print("\n[SUCCESS] Setup complete. Run `python run_pipeline.py` to start collection.")


if __name__ == "__main__":
    setup()
