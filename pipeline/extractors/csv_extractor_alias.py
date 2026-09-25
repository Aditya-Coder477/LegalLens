"""Alias module so dispatcher can import spreadsheet functions cleanly."""
from pipeline.extractors.spreadsheet_extractor import extract_csv, extract_xlsx, extract_xls

__all__ = ["extract_csv", "extract_xlsx", "extract_xls"]
