"""
LegalLens Data Collection Pipeline
===================================
Automated ingestion system for Indian legal data from authoritative sources.

Pipeline flow:
  Source → Discovery → Download → Raw Storage → Hash/Provenance →
  Validation → Text Extraction → OCR (if needed) → Metadata →
  Versioning → Deduplication → Domain Classification →
  Quality Check → Catalogue → Quality Report
"""

__version__ = "1.0.0"
__author__ = "LegalLens"
