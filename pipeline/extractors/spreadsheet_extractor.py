"""
pipeline/extractors/spreadsheet_extractor.py
=============================================
Extracts structured data from CSV, XLS, and XLSX files.
Each row (or sheet) becomes a PageRecord.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.core.metadata import ExtractionMethod, LegalDomain, PageRecord
from pipeline.core.logger import get_logger

log = get_logger("spreadsheet_extractor")


def _rows_to_records(
    rows: list[dict],
    document_id: str,
    source_url: str,
    legal_domain: str,
    extraction_method: ExtractionMethod,
    sheet_name: str = "",
) -> list[PageRecord]:
    """Convert a list of dicts (from pandas) into PageRecord objects."""
    records = []
    for i, row in enumerate(rows, start=1):
        # Flatten row to readable text
        parts = [f"{k}: {v}" for k, v in row.items() if str(v).strip() not in ("", "nan")]
        text = "\n".join(parts)
        if not text.strip():
            continue
        records.append(
            PageRecord(
                document_id=document_id,
                page=i,
                heading=sheet_name or None,
                text=text,
                source_url=source_url,
                legal_domain=legal_domain,
                extraction_method=extraction_method,
            )
        )
    return records


def extract_csv(
    csv_path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str = LegalDomain.UNCLASSIFIED.value,
) -> list[PageRecord]:
    """Extract rows from a CSV file."""
    try:
        import pandas as pd
    except ImportError as e:
        raise ImportError("pandas is required. Install: pip install pandas") from e

    try:
        df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip")
    except Exception:
        df = pd.read_csv(csv_path, dtype=str, encoding="latin-1", on_bad_lines="skip")

    rows = df.fillna("").to_dict(orient="records")
    records = _rows_to_records(
        rows, document_id=document_id, source_url=source_url,
        legal_domain=legal_domain, extraction_method=ExtractionMethod.CSV,
    )
    log.info("CSV extraction complete", document_id=document_id, rows=len(records))
    return records


def extract_xlsx(
    xlsx_path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str = LegalDomain.UNCLASSIFIED.value,
) -> list[PageRecord]:
    """Extract rows from an XLSX file (all sheets)."""
    try:
        import pandas as pd
    except ImportError as e:
        raise ImportError("pandas is required. Install: pip install pandas openpyxl") from e

    all_records: list[PageRecord] = []
    sheets = pd.read_excel(xlsx_path, sheet_name=None, dtype=str, engine="openpyxl")
    for sheet_name, df in sheets.items():
        rows = df.fillna("").to_dict(orient="records")
        all_records.extend(
            _rows_to_records(
                rows, document_id=document_id, source_url=source_url,
                legal_domain=legal_domain, extraction_method=ExtractionMethod.XLSX,
                sheet_name=str(sheet_name),
            )
        )
    log.info("XLSX extraction complete", document_id=document_id, rows=len(all_records))
    return all_records


def extract_xls(
    xls_path: Path,
    document_id: str,
    source_url: str,
    legal_domain: str = LegalDomain.UNCLASSIFIED.value,
) -> list[PageRecord]:
    """Extract rows from a legacy XLS file."""
    try:
        import pandas as pd
    except ImportError as e:
        raise ImportError("pandas is required. Install: pip install pandas xlrd") from e

    all_records: list[PageRecord] = []
    sheets = pd.read_excel(xls_path, sheet_name=None, dtype=str, engine="xlrd")
    for sheet_name, df in sheets.items():
        rows = df.fillna("").to_dict(orient="records")
        all_records.extend(
            _rows_to_records(
                rows, document_id=document_id, source_url=source_url,
                legal_domain=legal_domain, extraction_method=ExtractionMethod.XLS,
                sheet_name=str(sheet_name),
            )
        )
    log.info("XLS extraction complete", document_id=document_id, rows=len(all_records))
    return all_records
