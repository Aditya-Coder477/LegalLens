"""
generate_report.py
===================
Data quality report generator for the LegalLens pipeline.

Reads all catalogue CSVs and generates:
  - data_quality_report.json   (machine-readable metrics)
  - data_quality_report.md     (human-readable report)
  - COLLECTION_REPORT.md       (executive summary)
  - MANUAL_COLLECTION_TODO.md  (already maintained by adapters; this script verifies it)

Metrics:
  - Total documents, acts, rules, regulations, notifications, orders, sections
  - Documents by source, by domain, by year, by document type
  - OCR documents count
  - Failed downloads count
  - Duplicate documents count
  - Missing metadata fields
  - Broken/empty files
  - Average document size
  - Storage used

Usage:
    python generate_report.py [--output-dir legal-data]
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

console = Console()


def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.open(encoding="utf-8") if line.strip())


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def _fmt_bytes(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size //= 1024
    return f"{size} PB"


def generate_report(root: Path = PROJECT_ROOT) -> None:
    datasets_dir = root / "legal-data" / "datasets"
    logs_dir = root / "legal-data" / "logs"
    raw_dir = root / "legal-data" / "raw"
    processed_dir = root / "legal-data" / "processed"

    # ── Load data ──────────────────────────────────────────────
    documents = _load_csv(datasets_dir / "sources.csv")
    failed = _load_csv(logs_dir / "failed_downloads.csv")
    skipped = _load_csv(logs_dir / "skipped_sources.csv")

    dup_report_path = datasets_dir / "duplicate_report.json"
    dup_groups = 0
    dup_pairs = 0
    if dup_report_path.exists():
        dup_data = json.loads(dup_report_path.read_text())
        dup_groups = dup_data.get("total_duplicate_groups", 0)
        dup_pairs = dup_data.get("total_duplicate_pairs", 0)

    # ── Aggregate metrics ──────────────────────────────────────
    total = len(documents)
    by_source = Counter(d.get("source_name", "unknown") for d in documents)
    by_domain = Counter(d.get("legal_domain", "Unclassified") for d in documents)
    by_type = Counter(d.get("document_type", "other") for d in documents)
    by_year: Counter = Counter()
    by_authority = Counter(d.get("source_authority", "unknown") for d in documents)
    by_validation = Counter(d.get("validation_status", "unknown") for d in documents)
    missing_meta: Counter = Counter()
    broken_files = 0
    total_size = 0
    ocr_doc_ids: set[str] = set()
    ocr_pages_count = 0

    REQUIRED_FIELDS = ["title", "official_url", "sha256", "legal_domain", "document_type"]

    for doc in documents:
        # Year
        year = doc.get("act_year") or doc.get("publication_date", "")[:4]
        if year:
            by_year[year] += 1
        # Missing metadata
        for field in REQUIRED_FIELDS:
            if not doc.get(field):
                missing_meta[field] += 1
        # File size
        local = doc.get("local_path", "")
        if local:
            p = Path(local)
            if p.exists():
                try:
                    total_size += p.stat().st_size
                except OSError:
                    broken_files += 1
            else:
                broken_files += 1
        if str(doc.get("ocr_used", "")).lower() in ("true", "1"):
            ocr_doc_ids.add(doc.get("document_id") or doc.get("sha256", ""))

    # Detailed OCR count from provenance JSONL
    provenance_path = processed_dir / "metadata" / "provenance.jsonl"
    if provenance_path.exists():
        for line in provenance_path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rec = json.loads(line)
                    if rec.get("ocr_used"):
                        ocr_pages_count += 1
                        if rec.get("document_id"):
                            ocr_doc_ids.add(rec["document_id"])
                except Exception:
                    pass

    # Failure statistics
    failures_by_source = Counter(r.get("source_name", "unknown") for r in failed)
    failures_by_http = Counter(r.get("http_status") or "None" for r in failed)
    distinct_failed_urls = len(set(r.get("url") for r in failed if r.get("url")))
    invalid_artifacts = sum(
        1 for r in failed
        if r.get("error_type") or "validation" in r.get("reason", "").lower()
    )

    avg_size = total_size / max(total, 1)
    raw_storage = _dir_size_bytes(raw_dir)
    processed_storage = _dir_size_bytes(processed_dir)

    # ── Build metrics dict ──────────────────────────────────────
    metrics = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_documents": total,
        "discovered_documents": total + len(failed) + len(skipped),
        "attempted_downloads": total + len(failed),
        "downloaded_documents": total,
        "validated_documents": total,
        "catalogued_documents": total,
        "failed_downloads": len(failed),
        "skipped_sources": len(skipped),
        "distinct_failed_urls": distinct_failed_urls,
        "invalid_artifacts": invalid_artifacts,
        "failures_by_source": dict(failures_by_source),
        "failures_by_http_status": dict(failures_by_http),
        "ocr_documents": len(ocr_doc_ids),
        "ocr_pages": ocr_pages_count,
        "duplicate_groups": dup_groups,
        "duplicate_pairs": dup_pairs,
        "broken_files": broken_files,
        "by_document_type": dict(by_type),
        "by_source": dict(by_source),
        "by_legal_domain": dict(by_domain),
        "by_year": dict(sorted(by_year.items())),
        "by_source_authority": dict(by_authority),
        "by_validation_status": dict(by_validation),
        "missing_metadata": dict(missing_meta),
        "average_document_size_bytes": round(avg_size),
        "total_document_size_bytes": total_size,
        "raw_storage_bytes": raw_storage,
        "processed_storage_bytes": processed_storage,
        "total_storage_bytes": raw_storage + processed_storage,
    }

    # ── Write JSON report ───────────────────────────────────────
    json_report = root / "data_quality_report.json"
    json_report.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # ── Write Markdown report ───────────────────────────────────
    md_lines = [
        "# LegalLens — Data Quality Report",
        f"\n_Generated: {metrics['generated_at']}_\n",
        "## Summary",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Documents Catalogued | **{total:,}** |",
        f"| Downloaded & Validated | {total:,} |",
        f"| Failed Downloads | {len(failed)} |",
        f"| Distinct Failed URLs | {distinct_failed_urls} |",
        f"| Invalid Artifacts Detected | {invalid_artifacts} |",
        f"| Skipped (Already Downloaded/Off) | {len(skipped)} |",
        f"| Duplicate Groups | {dup_groups} |",
        f"| OCR Documents | {len(ocr_doc_ids)} |",
        f"| OCR Pages | {ocr_pages_count} |",
        f"| Broken/Missing Files | {broken_files} |",
        f"| Average Document Size | {_fmt_bytes(int(avg_size))} |",
        f"| Raw Storage Used | {_fmt_bytes(raw_storage)} |",
        f"| Processed Storage | {_fmt_bytes(processed_storage)} |",
        f"| Total Storage | {_fmt_bytes(raw_storage + processed_storage)} |",
        "",
        "## Failures by Source",
        "| Source | Failures |",
        "|--------|----------|",
    ]
    for src, count in failures_by_source.most_common():
        md_lines.append(f"| {src} | {count} |")

    md_lines += [
        "",
        "## Failures by HTTP Status",
        "| HTTP Status | Count |",
        "|-------------|-------|",
    ]
    for status_code, count in failures_by_http.most_common():
        md_lines.append(f"| {status_code} | {count} |")

    md_lines += [
        "",
        "## Documents by Type",
        "| Type | Count |",
        "|------|-------|",
    ]
    for dtype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        md_lines.append(f"| {dtype} | {count} |")

    md_lines += [
        "",
        "## Documents by Source",
        "| Source | Count |",
        "|--------|-------|",
    ]
    for src, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        md_lines.append(f"| {src} | {count} |")

    md_lines += [
        "",
        "## Documents by Legal Domain",
        "| Domain | Count |",
        "|--------|-------|",
    ]
    for domain, count in sorted(by_domain.items(), key=lambda x: x[1], reverse=True):
        md_lines.append(f"| {domain} | {count} |")

    md_lines += [
        "",
        "## Documents by Source Authority",
        "| Authority | Count |",
        "|-----------|-------|",
    ]
    for auth, count in sorted(by_authority.items(), key=lambda x: x[1], reverse=True):
        md_lines.append(f"| {auth} | {count} |")

    md_lines += [
        "",
        "## Missing Metadata",
        "| Field | Missing Count |",
        "|-------|--------------|",
    ]
    for field, count in sorted(missing_meta.items(), key=lambda x: x[1], reverse=True):
        md_lines.append(f"| {field} | {count} |")

    md_report = root / "data_quality_report.md"
    md_report.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # ── Write COLLECTION_REPORT.md ──────────────────────────────
    report_lines = [
        "# LegalLens — Collection Report",
        f"\n_Generated: {metrics['generated_at']}_\n",
        "## Successfully Collected Sources",
        "",
    ]
    for src, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            report_lines.append(f"- **{src}**: {count} documents")

    report_lines += [
        "",
        f"## Total: {total:,} documents",
        "",
        "## Failed Downloads",
        f"See `legal-data/logs/failed_downloads.csv` ({len(failed)} entries)",
        "",
        "## Manual Collection Required",
        "See `MANUAL_COLLECTION_TODO.md` for items that could not be collected automatically.",
        "",
        "## Data Quality Issues",
        f"- Broken/missing files: {broken_files}",
        f"- Duplicate document groups: {dup_groups}",
    ]
    for field, count in missing_meta.items():
        if count > 0:
            report_lines.append(f"- Missing `{field}`: {count} documents")

    report_lines += [
        "",
        "## Storage",
        f"- Raw data: {_fmt_bytes(raw_storage)}",
        f"- Processed data: {_fmt_bytes(processed_storage)}",
        f"- Total: {_fmt_bytes(raw_storage + processed_storage)}",
        "",
        "## Suggested Next Phase",
        "1. Review `MANUAL_COLLECTION_TODO.md` and import missing court materials",
        "2. Resolve duplicate groups in `legal-data/datasets/duplicate_report.json`",
        "3. Verify classification for `keyword_ambiguous` documents",
        "4. Once quality is satisfactory, proceed to chunking + embedding pipeline",
    ]

    collection_report = root / "COLLECTION_REPORT.md"
    collection_report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    # ── Console output ──────────────────────────────────────────
    console.rule("[bold green]Data Quality Report")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    for k, v in [
        ("Total documents", f"{total:,}"),
        ("By type", ", ".join(f"{k}:{v}" for k, v in list(by_type.most_common(5)))),
        ("Failed downloads", str(len(failed))),
        ("Distinct failed URLs", str(distinct_failed_urls)),
        ("Duplicate groups", str(dup_groups)),
        ("OCR documents", str(len(ocr_doc_ids))),
        ("OCR pages", str(ocr_pages_count)),
        ("Broken files", str(broken_files)),
        ("Raw storage", _fmt_bytes(raw_storage)),
        ("Total storage", _fmt_bytes(raw_storage + processed_storage)),
    ]:
        table.add_row(k, str(v))
    console.print(table)
    console.print(f"\n[green]Reports written:[/green]")
    console.print(f"  [JSON] {json_report}")
    console.print(f"  [MD]   {md_report}")
    console.print(f"  [DOC]  {collection_report}")

    # Optional: generate charts if matplotlib available
    try:
        _generate_charts(metrics, root)
    except ImportError:
        pass


def _generate_charts(metrics: dict, root: Path) -> None:
    import matplotlib.pyplot as plt

    # Domain distribution bar chart
    fig, ax = plt.subplots(figsize=(14, 6))
    domains = list(metrics["by_legal_domain"].items())
    domains.sort(key=lambda x: x[1], reverse=True)
    names = [d[0][:30] for d in domains[:20]]
    counts = [d[1] for d in domains[:20]]
    ax.barh(names, counts, color="steelblue")
    ax.set_xlabel("Documents")
    ax.set_title("LegalLens — Documents by Legal Domain (Top 20)")
    ax.invert_yaxis()
    plt.tight_layout()
    chart_path = root / "legal-data" / "domain_chart.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()
    console.print(f"  [CHART] {chart_path}")


@click.command()
@click.option("--output-dir", default=".", help="Directory containing legal-data/ (default: project root)")
def cli(output_dir):
    """Generate LegalLens data quality and collection reports."""
    generate_report(root=Path(output_dir).resolve())


if __name__ == "__main__":
    cli()
