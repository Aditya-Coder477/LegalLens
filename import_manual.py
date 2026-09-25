"""
import_manual.py
=================
Manual file import utility for the LegalLens pipeline.

Allows you to manually download files that cannot be collected automatically
(e.g. eCourts judgments, password-protected portals) and run them through
the full pipeline: hash → type detection → metadata → copy to raw/ →
extract text → classify → deduplicate → update sources.csv.

Usage:
    python import_manual.py path/to/file.pdf [OPTIONS]

Required:
    FILE            Path to the local file to import

Options:
    --source TEXT       Source ID (india_code, ecourts, supreme_court, nalsa, etc.)
    --doc-type TEXT     Document type (act, judgment, rule, regulation, etc.)
    --domain TEXT       Legal domain (e.g. "Criminal Law")
    --title TEXT        Document title (prompted if not provided)
    --url TEXT          Original source URL (for provenance)
    --date TEXT         Publication date (YYYY-MM-DD)
    --ministry TEXT     Ministry/department
    --act-number TEXT   Act number
    --act-year INT      Act year

Examples:
    python import_manual.py ~/Downloads/judgment_2024.pdf \\
        --source supreme_court \\
        --doc-type judgment \\
        --domain "Constitutional Law" \\
        --title "Kesavananda Bharati vs State of Kerala" \\
        --url "https://sci.gov.in/..." \\
        --date 1973-04-24

    python import_manual.py ~/Downloads/IPC_1860.pdf \\
        --source india_code \\
        --doc-type act \\
        --domain "Criminal Law" \\
        --title "Indian Penal Code, 1860" \\
        --url "https://www.indiacode.nic.in/handle/123456789/15289" \\
        --act-number "45" --act-year 1860
"""

from __future__ import annotations

import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import click

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.core.catalogue import Catalogue
from pipeline.core.config import get_config
from pipeline.core.hasher import sha256_file
from pipeline.core.logger import get_logger
from pipeline.core.metadata import (
    CollectionMethod, DocumentMetadata, DocumentStatus, DocumentType,
    LegalDomain, SourceAuthority,
)
from pipeline.classification.classifier import classify_document
from pipeline.extractors.dispatcher import extract, detect_format
from pipeline.versioning.version_tracker import VersionTracker

log = get_logger("import_manual")

SOURCE_AUTHORITY_MAP = {
    "india_code": SourceAuthority.PRIMARY_OFFICIAL,
    "legislative_dept": SourceAuthority.PRIMARY_OFFICIAL,
    "supreme_court": SourceAuthority.OFFICIAL_COURT,
    "ecourts": SourceAuthority.OFFICIAL_COURT,
    "nalsa": SourceAuthority.OFFICIAL_LEGAL_AID,
    "data_gov": SourceAuthority.OFFICIAL_GOVERNMENT,
    "meity": SourceAuthority.OFFICIAL_GOVERNMENT,
    "india_code_api": SourceAuthority.SECONDARY_COMMUNITY,
}

RAW_DIR_MAP = {
    "india_code": "legal-data/raw/india_code",
    "ecourts": "legal-data/raw/ecourts",
    "supreme_court": "legal-data/raw/supreme_court",
    "nalsa": "legal-data/raw/nalsa",
    "legislative_dept": "legal-data/raw/legislative_department",
    "meity": "legal-data/raw/meity",
    "data_gov": "legal-data/raw/data_gov",
    "india_code_api": "legal-data/raw/india_code/sections",
}

DOC_TYPE_MAP = {
    "act": DocumentType.ACT,
    "judgment": DocumentType.JUDGMENT,
    "rule": DocumentType.RULE,
    "regulation": DocumentType.REGULATION,
    "notification": DocumentType.NOTIFICATION,
    "order": DocumentType.ORDER,
    "ordinance": DocumentType.ORDINANCE,
    "circular": DocumentType.CIRCULAR,
    "statute": DocumentType.STATUTE,
    "dataset": DocumentType.DATASET,
    "report": DocumentType.REPORT,
    "guideline": DocumentType.GUIDELINE,
    "bill": DocumentType.BILL,
    "constitution": DocumentType.CONSTITUTION,
    "amendment": DocumentType.AMENDMENT,
    "other": DocumentType.OTHER,
}


@click.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--source", default="other", help="Source ID")
@click.option("--doc-type", "doc_type", default="other", help="Document type")
@click.option("--domain", default=None, help="Legal domain")
@click.option("--title", default=None, help="Document title")
@click.option("--url", default=None, help="Original source URL")
@click.option("--date", "pub_date", default=None, help="Publication date (YYYY-MM-DD)")
@click.option("--ministry", default=None, help="Ministry/department")
@click.option("--act-number", default=None, help="Act number")
@click.option("--act-year", default=None, type=int, help="Act year")
@click.option("--enable-llm", is_flag=True, default=False, help="Use LLM classifier")
def main(
    file_path: Path,
    source: str,
    doc_type: str,
    domain: str | None,
    title: str | None,
    url: str | None,
    pub_date: str | None,
    ministry: str | None,
    act_number: str | None,
    act_year: int | None,
    enable_llm: bool,
) -> None:
    """Import a manually downloaded file into the LegalLens pipeline."""
    cfg = get_config()

    click.echo(f"\n📥 Importing: {file_path}")

    # 1. Hash the file
    sha256 = sha256_file(file_path)
    click.echo(f"🔐 SHA-256: {sha256}")

    # 2. Detect format
    try:
        fmt = detect_format(file_path)
        click.echo(f"📄 Format: {fmt}")
    except ValueError as exc:
        click.echo(f"⚠ Format detection: {exc} — defaulting to 'other'")
        fmt = "other"

    # 3. Prompt for missing metadata
    if not title:
        title = click.prompt(
            "Document title",
            default=file_path.stem.replace("_", " ").replace("-", " ").title()
        )
    if not url:
        url = click.prompt("Original source URL (for provenance)", default="unknown")

    # 4. Classify domain
    if domain:
        primary_domain = domain
        secondary_domains: list[str] = []
        confidence = 1.0
        class_method = "manual"
    else:
        primary_domain, secondary_domains, confidence, class_method = classify_document(
            title=title,
            ministry=ministry or "",
            act_number=act_number or "",
            enable_llm=enable_llm,
        )
        click.echo(f"🏷 Classified: {primary_domain} (confidence={confidence:.2f}, method={class_method})")

    # 5. Copy to raw directory
    raw_base = RAW_DIR_MAP.get(source, f"legal-data/raw/{source}")
    dest_dir = Path(raw_base)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file_path.name
    if dest.exists():
        existing_hash = sha256_file(dest)
        if existing_hash == sha256:
            click.echo(f"⏭ File already in raw/ with same hash — skipping copy")
        else:
            # Different content with same filename — add UUID suffix
            dest = dest_dir / f"{file_path.stem}_{uuid4().hex[:6]}{file_path.suffix}"
            shutil.copy2(file_path, dest)
            click.echo(f"📁 Copied (renamed) to: {dest}")
    else:
        shutil.copy2(file_path, dest)
        click.echo(f"📁 Copied to: {dest}")

    # 6. Parse publication date
    parsed_date = None
    if pub_date:
        try:
            parsed_date = date.fromisoformat(pub_date)
        except ValueError:
            click.echo(f"⚠ Could not parse date: {pub_date}")

    # 7. Extract text
    try:
        page_records = extract(
            file_path=dest,
            document_id=sha256[:12],
            source_url=url,
            legal_domain=primary_domain,
            ocr_mode=cfg.ocr.mode,
        )
        click.echo(f"📖 Extracted {len(page_records)} pages/sections")
        # Save extracted pages
        import json
        pages_dir = Path("legal-data/processed/pages")
        pages_dir.mkdir(parents=True, exist_ok=True)
        pages_file = pages_dir / f"{sha256[:12]}.jsonl"
        with pages_file.open("w", encoding="utf-8") as f:
            for record in page_records:
                f.write(record.model_dump_json() + "\n")
        click.echo(f"💾 Pages saved to: {pages_file}")
    except Exception as exc:
        click.echo(f"⚠ Text extraction failed: {exc}")
        page_records = []

    # 8. Version tracking
    version_tracker = VersionTracker()
    version_tracker.load(output_dir=cfg.storage.datasets_dir)
    doc_meta_temp = DocumentMetadata(
        source_id="temp",
        source_name=source,
        source_type="manual",
        source_authority=SOURCE_AUTHORITY_MAP.get(source, SourceAuthority.USER_PROVIDED),
        legal_domain=primary_domain,
        title=title,
        document_type=DOC_TYPE_MAP.get(doc_type, DocumentType.OTHER),
        official_url=url,
        act_number=act_number,
        act_year=act_year,
        publication_date=parsed_date,
        sha256=sha256,
    )
    group_id, version_label = version_tracker.assign_version(doc_meta_temp)
    version_tracker.save(output_dir=cfg.storage.datasets_dir)

    # 9. Build final metadata and upsert to catalogue
    source_authority = SOURCE_AUTHORITY_MAP.get(source, SourceAuthority.USER_PROVIDED)
    doc_meta = DocumentMetadata(
        source_id=f"manual_{uuid4().hex[:8]}",
        source_name=source,
        source_type="manual_import",
        source_authority=source_authority,
        legal_domain=primary_domain,
        secondary_domains=secondary_domains,
        classification_confidence=confidence,
        classification_method=class_method,
        title=title,
        document_type=DOC_TYPE_MAP.get(doc_type, DocumentType.OTHER),
        official_url=url,
        local_path=str(dest),
        file_format=fmt,
        publication_date=parsed_date,
        ministry=ministry,
        act_number=act_number,
        act_year=act_year,
        sha256=sha256,
        file_size_bytes=dest.stat().st_size,
        download_timestamp=datetime.utcnow(),
        collection_method=CollectionMethod.MANUAL,
        document_version_group_id=group_id,
        version_label=version_label,
    )

    catalogue = Catalogue(
        datasets_dir=cfg.storage.datasets_dir,
        logs_dir=cfg.storage.logs_dir,
    )
    catalogue.load()
    catalogue.upsert_document(doc_meta)

    click.echo(f"\n✅ Import complete!")
    click.echo(f"   Title: {title}")
    click.echo(f"   Domain: {primary_domain}")
    click.echo(f"   Source authority: {source_authority.value}")
    click.echo(f"   Version group: {group_id}")
    click.echo(f"   SHA-256: {sha256}")
    click.echo(f"   Stored: {dest}")


if __name__ == "__main__":
    main()
