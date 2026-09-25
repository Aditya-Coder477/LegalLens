"""
run_pipeline.py
================
Main pipeline orchestrator for the LegalLens data collection system.

Usage:
    python run_pipeline.py [OPTIONS]

Options:
    --sources TEXT      Comma-separated source IDs to run
                        (default: all enabled in config.yaml)
                        Available: india_code, india_code_api, data_gov,
                                   ecourts, supreme_court, nalsa,
                                   legislative_dept, meity
    --resume            Skip already-downloaded URLs/hashes (default: True)
    --no-resume         Force re-download everything
    --dry-run           Log what would be collected without downloading
    --limit INT         Max documents per source (useful for testing)
    --enable-llm        Enable LLM domain classifier for ambiguous docs
    --year-from INT     Override year_from for all sources
    --year-to INT       Override year_to for all sources
    --no-ocr            Disable inline OCR for this run

Examples:
    # Dry-run test with 3 documents per source
    python run_pipeline.py --sources nalsa,meity --limit 3 --dry-run

    # Full resumable collection
    python run_pipeline.py --resume

    # Collect India Code with LLM classifier
    python run_pipeline.py --sources india_code --enable-llm
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import click
from rich.console import Console
from rich.table import Table

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.core.catalogue import Catalogue
from pipeline.core.config import get_config, reload_config
from pipeline.core.logger import get_logger
from pipeline.dedup.deduplicator import Deduplicator
from pipeline.versioning.version_tracker import VersionTracker
from source_check import display_results, run_diagnostics

console = Console()
log = get_logger("run_pipeline")

# ── Available adapters (import lazily to avoid startup overhead) ──
ADAPTER_MAP = {
    "india_code": "pipeline.adapters.india_code",
    "india_code_api": "pipeline.adapters.india_code_api",
    "data_gov": "pipeline.adapters.data_gov",
    "ecourts": "pipeline.adapters.ecourts",
    "supreme_court": "pipeline.adapters.supreme_court",
    "nalsa": "pipeline.adapters.nalsa",
    "legislative_dept": "pipeline.adapters.legislative_dept",
    "meity": "pipeline.adapters.meity",
}

SOURCE_RAW_DIRS = {
    "india_code": "legal-data/raw/india_code",
    "india_code_api": "legal-data/raw/india_code/sections",
    "data_gov": "legal-data/raw/data_gov",
    "ecourts": "legal-data/raw/ecourts",
    "supreme_court": "legal-data/raw/supreme_court",
    "nalsa": "legal-data/raw/nalsa",
    "legislative_dept": "legal-data/raw/legislative_department",
    "meity": "legal-data/raw/meity",
}


def _is_source_enabled(source_id: str, cfg) -> bool:
    """Check if a source is enabled in config."""
    src_cfg = getattr(cfg.sources, source_id, None)
    if src_cfg is None:
        return False
    return getattr(src_cfg, "enabled", True)


async def run_source(
    source_id: str,
    catalogue: Catalogue,
    version_tracker: VersionTracker,
    cfg,
    limit: int | None,
    resume: bool,
    dry_run: bool,
    enable_llm: bool,
    run_id: str,
) -> dict:
    """Run a single source adapter and return stats."""
    import importlib

    module_path = ADAPTER_MAP.get(source_id)
    if not module_path:
        log.warning("Unknown source", source_id=source_id)
        return {"source": source_id, "collected": 0, "error": "unknown_source"}

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        log.error("Failed to import adapter", source=source_id, error=str(exc))
        return {"source": source_id, "collected": 0, "error": str(exc)}

    raw_dir = SOURCE_RAW_DIRS.get(source_id, f"legal-data/raw/{source_id}")
    start_time = time.monotonic()

    try:
        collected = await module.collect(
            catalogue=catalogue,
            raw_dir=raw_dir,
            limit=limit,
            resume=resume,
            dry_run=dry_run,
        )
    except Exception as exc:
        log.error("Source collection failed", source=source_id, error=str(exc))
        return {"source": source_id, "collected": 0, "error": str(exc)}

    elapsed = time.monotonic() - start_time
    return {
        "source": source_id,
        "collected": collected,
        "elapsed_seconds": round(elapsed, 1),
        "error": None,
    }


async def main(
    sources: list[str],
    limit: int | None,
    resume: bool,
    dry_run: bool,
    enable_llm: bool,
    year_from: int | None,
    year_to: int | None,
    no_ocr: bool,
) -> None:
    cfg = get_config()
    run_id = str(uuid4())

    if enable_llm:
        # Override config to enable LLM for this run
        cfg.classification.llm_classifier_enabled = True
        log.info("LLM classifier enabled for this run")

    if no_ocr:
        cfg.ocr.mode = "offline"
        log.info("OCR deferred (offline mode)")

    # Setup
    console.rule("[bold blue]LegalLens Pipeline")
    console.print(f"[cyan]Run ID:[/cyan] {run_id}")
    console.print(f"[cyan]Started:[/cyan] {datetime.utcnow().isoformat()}Z")
    console.print(f"[cyan]Sources:[/cyan] {', '.join(sources)}")
    console.print(f"[cyan]Mode:[/cyan] {'DRY RUN (no documents stored)' if dry_run else 'LIVE'} | resume={resume}")
    if limit:
        console.print(f"[cyan]Limit:[/cyan] {limit} documents per source")

    # Initialise catalogue
    catalogue = Catalogue(
        datasets_dir=cfg.storage.datasets_dir,
        logs_dir=cfg.storage.logs_dir,
    )
    catalogue.load()
    initial_docs_count = len(catalogue.documents)

    # Initialise version tracker
    version_tracker = VersionTracker()
    version_tracker.load(output_dir=cfg.storage.datasets_dir)

    # Run sources sequentially (respect rate limits)
    results = []
    for source_id in sources:
        if not _is_source_enabled(source_id, cfg):
            log.info("Source disabled in config — skipping", source=source_id)
            results.append({"source": source_id, "collected": 0, "error": "disabled_in_config"})
            continue

        console.rule(f"[bold yellow]Source: {source_id}")
        result = await run_source(
            source_id=source_id,
            catalogue=catalogue,
            version_tracker=version_tracker,
            cfg=cfg,
            limit=limit,
            resume=resume,
            dry_run=dry_run,
            enable_llm=enable_llm,
            run_id=run_id,
        )
        results.append(result)
        doc_label = "would collect" if dry_run else "documents"
        console.print(
            f"  {'[SUCCESS]' if not result['error'] else '[FAILED]'} "
            f"[bold]{source_id}:[/bold] {result['collected']} {doc_label}"
            + (f" in {result.get('elapsed_seconds', '?')}s" if not result.get('error') else f" — {result['error']}")
        )

    # Run deduplication
    if not dry_run:
        console.rule("[bold]Deduplication")
        dedup_cfg = cfg.dedup
        deduplicator = Deduplicator(similarity_threshold=dedup_cfg.similarity_threshold)
        dup_groups = deduplicator.run(catalogue.documents)
        deduplicator.save_report(dup_groups, output_dir=cfg.storage.datasets_dir)
        console.print(f"  Duplicate groups found: {len(dup_groups)}")

    # Save version groups
    if not dry_run:
        version_tracker.save(output_dir=cfg.storage.datasets_dir)

    # Print summary table
    console.rule("[bold green]Collection Summary")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Source")
    table.add_column("Would Collect" if dry_run else "Catalogued Docs", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("Status")

    total = 0
    for r in results:
        status = "[OK]" if not r.get("error") else f"[FAIL] {r.get('error', '')[:40]}"
        table.add_row(
            r["source"],
            str(r["collected"]),
            str(r.get("elapsed_seconds", "-")),
            status,
        )
        total += r["collected"]
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]", "", "")
    console.print(table)

    if dry_run:
        console.print("\n[yellow][DRY RUN][/yellow] Simulated run complete. 0 documents stored to disk.")
    else:
        newly_catalogued = len(catalogue.documents) - initial_docs_count
        console.print(f"\n[green]Run complete.[/green] Newly catalogued documents: [bold]{newly_catalogued}[/bold]")
        console.print(
            "Run [bold]python generate_report.py[/bold] to generate the comprehensive data quality report."
        )


@click.command()
@click.option(
    "--sources", default=None,
    help="Comma-separated source IDs. Default: all enabled in config.yaml"
)
@click.option("--resume/--no-resume", default=True, help="Skip already-downloaded files")
@click.option("--dry-run", is_flag=True, default=False, help="Log without downloading")
@click.option("--limit", default=None, type=int, help="Max documents per source")
@click.option("--enable-llm", is_flag=True, default=False, help="Enable LLM classifier")
@click.option("--year-from", default=None, type=int)
@click.option("--year-to", default=None, type=int)
@click.option("--no-ocr", is_flag=True, default=False, help="Disable inline OCR")
@click.option("--check-sources", is_flag=True, default=False, help="Run source preflight diagnostics")
def cli(sources, resume, dry_run, limit, enable_llm, year_from, year_to, no_ocr, check_sources):
    """LegalLens Automated Legal Data Collection Pipeline."""
    if check_sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
        results = asyncio.run(run_diagnostics(source_list))
        display_results(results)
        return

    cfg = get_config()

    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        # Default: all enabled sources in order
        source_list = [
            s for s in ADAPTER_MAP.keys()
            if _is_source_enabled(s, cfg)
        ]

    asyncio.run(
        main(
            sources=source_list,
            limit=limit,
            resume=resume,
            dry_run=dry_run,
            enable_llm=enable_llm,
            year_from=year_from,
            year_to=year_to,
            no_ocr=no_ocr,
        )
    )


if __name__ == "__main__":
    cli()
