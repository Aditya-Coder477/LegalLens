"""
pipeline/core/metadata.py
=========================
Pydantic v2 data models used throughout the LegalLens pipeline.

These models define the canonical schema for:
  - DocumentMetadata  → one row in sources.csv / documents.csv
  - PageRecord        → one extracted page (output of all extractors)
  - SectionRecord     → a logical legal section
  - ChunkRecord       → a retrieval chunk (future RAG use)
  - ProvenanceRecord  → audit chain from chunk → page → document → URL
  - FailedDownload    → one row in failed_downloads.csv
  - SkippedSource     → one row in skipped_sources.csv
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ──────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────

class SourceAuthority(str, Enum):
    """Evidence chain authority tier for a source."""
    PRIMARY_OFFICIAL = "PRIMARY_OFFICIAL"        # India Code, Legislative Dept
    OFFICIAL_COURT = "OFFICIAL_COURT"            # Supreme Court, High Courts
    OFFICIAL_GOVERNMENT = "OFFICIAL_GOVERNMENT"  # MeitY, data.gov.in
    OFFICIAL_LEGAL_AID = "OFFICIAL_LEGAL_AID"    # NALSA
    SECONDARY_COMMUNITY = "SECONDARY_COMMUNITY"  # indiacode.ecourtsindia.com
    USER_PROVIDED = "USER_PROVIDED"              # manually uploaded files
    SYNTHETIC = "SYNTHETIC"                      # evaluation / test data


class DocumentType(str, Enum):
    ACT = "act"
    SECTION = "section"
    RULE = "rule"
    REGULATION = "regulation"
    NOTIFICATION = "notification"
    ORDER = "order"
    ORDINANCE = "ordinance"
    STATUTE = "statute"
    CIRCULAR = "circular"
    JUDGMENT = "judgment"
    DATASET = "dataset"
    REPORT = "report"
    GUIDELINE = "guideline"
    GUIDELINES = "guideline"
    BILL = "bill"
    CONSTITUTION = "constitution"
    AMENDMENT = "amendment"
    CONTRACT = "contract"
    AGREEMENT = "agreement"
    OTHER = "other"
    RULES = "rule"


class DocumentStatus(str, Enum):
    ACTIVE = "active"
    REPEALED = "repealed"
    AMENDED = "amended"
    SUPERSEDED = "superseded"
    DRAFT = "draft"
    UNKNOWN = "unknown"


class CollectionMethod(str, Enum):
    API = "api"
    HTML_CRAWL = "html_crawl"
    DIRECT_DOWNLOAD = "direct_download"
    BITSTREAM = "bitstream"
    MANUAL = "manual"
    ECOURTSINDIA_API = "ecourtsindia_api"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    REQUIRES_REVIEW = "requires_review"


class ExtractionMethod(str, Enum):
    PDF_TEXT = "pdf_text"
    PDF_OCR = "pdf_ocr"
    PDF_MIXED = "pdf_mixed"   # some pages text, some OCR
    HTML = "html"
    DOCX = "docx"
    CSV = "csv"
    JSON_NATIVE = "json_native"
    XLSX = "xlsx"
    XLS = "xls"
    MARKDOWN = "markdown"


class LegalDomain(str, Enum):
    # ── Core Domains (1–20) ──────────────────
    CONSTITUTIONAL_LAW = "Constitutional Law"
    CONTRACT_LAW = "Contract Law"
    COMMERCIAL_CORPORATE = "Commercial and Corporate Law"
    EMPLOYMENT_LABOUR = "Employment and Labour Law"
    CONSUMER_LAW = "Consumer Law"
    CRIMINAL_LAW = "Criminal Law"
    CIVIL_PROCEDURE = "Civil Procedure"
    PROPERTY_REAL_ESTATE = "Property and Real Estate Law"
    FAMILY_LAW = "Family Law"
    INTELLECTUAL_PROPERTY = "Intellectual Property Law"
    IT_CYBER_LAW = "Information Technology and Cyber Law"
    DATA_PROTECTION_PRIVACY = "Data Protection and Privacy Law"
    TAX_LAW = "Tax Law"
    BANKING_FINANCIAL = "Banking and Financial Law"
    INSURANCE_LAW = "Insurance Law"
    ARBITRATION_ADR = "Arbitration and Alternative Dispute Resolution"
    ENVIRONMENTAL_LAW = "Environmental Law"
    LAND_PROPERTY = "Land and Property Law"
    ADMINISTRATIVE_LAW = "Administrative Law"
    PUBLIC_FINANCIAL_GRIEVANCE = "Public/Financial Grievance-related Law"
    # ── Secondary Domains (21–50) ────────────
    INSOLVENCY_BANKRUPTCY = "Insolvency and Bankruptcy"
    SECURITIES_CAPITAL_MARKETS = "Securities and Capital Markets"
    COMPETITION_LAW = "Competition Law"
    TELECOMMUNICATIONS = "Telecommunications Law"
    MEDIA_ENTERTAINMENT = "Media and Entertainment Law"
    EDUCATION_LAW = "Education Law"
    HEALTH_MEDICAL = "Health and Medical Law"
    PHARMACEUTICAL = "Pharmaceutical Law"
    FOOD_SAFETY = "Food Safety Law"
    MOTOR_VEHICLE_TRANSPORT = "Motor Vehicle and Transport Law"
    AVIATION_LAW = "Aviation Law"
    MARITIME_LAW = "Maritime Law"
    ELECTRICITY_ENERGY = "Electricity and Energy Law"
    MINING_NATURAL_RESOURCES = "Mining and Natural Resources"
    AGRICULTURAL_LAW = "Agricultural Law"
    IMMIGRATION_CITIZENSHIP = "Immigration and Citizenship"
    ELECTION_ELECTORAL = "Election and Electoral Law"
    GOVERNMENT_SERVICE = "Government Service Law"
    PENSION_SOCIAL_WELFARE = "Pension and Social Welfare Law"
    HUMAN_RIGHTS = "Human Rights"
    CHILD_RIGHTS = "Child Rights"
    WOMEN_LAW = "Women-related Law"
    DISABILITY_RIGHTS = "Disability Rights"
    SENIOR_CITIZEN = "Senior Citizen Law"
    LOCAL_GOVERNMENT_MUNICIPAL = "Local Government and Municipal Law"
    PANCHAYATI_RAJ = "Panchayati Raj"
    PUBLIC_PROCUREMENT = "Public Procurement"
    FOREIGN_EXCHANGE_INVESTMENT = "Foreign Exchange and Foreign Investment"
    INTERNATIONAL_TRADE = "International Trade"
    EMERGING_TECHNOLOGY_AI = "Emerging Technology / AI / Digital Regulation"
    UNCLASSIFIED = "Unclassified"


# ──────────────────────────────────────────────
# Core Models
# ──────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    """
    28-field canonical document record.
    Maps 1:1 to a row in legal-data/datasets/sources.csv.
    """

    # ── Identity ─────────────────────────────
    source_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique document ID (UUID4)"
    )
    source_name: str = Field(description="Human-readable source name, e.g. 'India Code'")
    source_type: str = Field(description="Source category, e.g. 'legislation', 'judgment', 'dataset'")
    source_authority: SourceAuthority = Field(
        default=SourceAuthority.PRIMARY_OFFICIAL,
        description="Evidence chain authority tier"
    )

    # ── Legal domain ─────────────────────────
    legal_domain: str = Field(
        default=LegalDomain.UNCLASSIFIED.value,
        description="Primary legal domain (one of 50 defined domains)"
    )
    secondary_domains: list[str] = Field(
        default_factory=list,
        description="Additional applicable legal domains"
    )
    classification_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Classification confidence score (0.0–1.0)"
    )
    classification_method: Optional[str] = Field(
        default=None,
        description="'keyword', 'llm', or 'manual'"
    )

    # ── Document identity ─────────────────────
    title: str = Field(description="Full document title")
    document_type: DocumentType = Field(description="Type of legal document")
    official_url: Optional[str] = Field(default=None, description="Original source URL (preserved, never modified)")
    download_url: Optional[str] = Field(default=None, description="Direct download URL if different from official")

    # ── File storage ─────────────────────────
    local_path: Optional[str] = Field(default=None, description="Relative path under legal-data/raw/")
    file_format: Optional[str] = Field(default=None, description="pdf, html, docx, csv, json, xlsx, xls")

    # ── Dates ─────────────────────────────────
    publication_date: Optional[date] = Field(default=None)
    effective_date: Optional[date] = Field(default=None)
    repeal_date: Optional[date] = Field(default=None)
    amendment_date: Optional[date] = Field(default=None)

    # ── Status & jurisdiction ─────────────────
    status: DocumentStatus = Field(default=DocumentStatus.UNKNOWN)
    ministry: Optional[str] = Field(default=None)
    department: Optional[str] = Field(default=None)
    jurisdiction: str = Field(default="India")
    country: str = Field(default="IN")
    state: Optional[str] = Field(default=None, description="State/UT for state legislation")

    # ── Act metadata ─────────────────────────
    act_number: Optional[str] = Field(default=None, description="e.g. '9' for Act No. 9 of 1872")
    act_year: Optional[int] = Field(default=None)
    section_number: Optional[str] = Field(default=None)

    # ── Language ─────────────────────────────
    language: str = Field(default="en")
    original_language: Optional[str] = Field(default=None)
    translation_available: bool = Field(default=False)
    translation_source: Optional[str] = Field(default=None)

    # ── Integrity ────────────────────────────
    sha256: Optional[str] = Field(default=None, description="SHA-256 of the raw file")
    file_size_bytes: Optional[int] = Field(default=None)

    # ── Collection provenance ─────────────────
    download_timestamp: Optional[datetime] = Field(default=None)
    last_verified: Optional[datetime] = Field(default=None)
    collection_method: CollectionMethod = Field(default=CollectionMethod.DIRECT_DOWNLOAD)
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    http_status: Optional[int] = Field(default=None)
    content_type: Optional[str] = Field(default=None)
    etag: Optional[str] = Field(default=None)
    last_modified_header: Optional[str] = Field(default=None)

    # ── Versioning ───────────────────────────
    document_version_group_id: Optional[str] = Field(
        default=None,
        description="Groups all versions of the same act/document"
    )
    version_label: Optional[str] = Field(default=None, description="e.g. 'original', 'amended_2019'")

    # ── Identity Semantics & Pipeline Status ──
    document_id: Optional[str] = Field(default=None, description="Stable logical document identity (UUID5 or unique key)")
    source_instance_id: Optional[str] = Field(default=None, description="Identity of this specific source version")
    validation_status: str = Field(default="pending", description="valid, invalid, or pending")
    validation_error: Optional[str] = Field(default=None, description="Reason if artifact validation failed")
    extraction_status: str = Field(default="pending", description="success, partial, failed, or pending")
    extraction_method: Optional[str] = Field(default=None, description="Method used to extract text")
    ocr_used: bool = Field(default=False, description="Whether OCR was actually executed")
    ocr_pages: int = Field(default=0, description="Count of pages processed via OCR")
    extractor_version: str = Field(default="1.0.0", description="Extractor version")

    # ── DSpace / India Code specific ─────────
    dspace_handle: Optional[str] = Field(default=None, description="e.g. '123456789/2187'")
    act_id: Optional[str] = Field(default=None, description="India Code numeric actid")
    synthetic: bool = Field(default=False, description="Flag indicating synthetic test data")

    @field_validator("sha256")
    @classmethod
    def sha256_must_be_hex64(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) != 64:
            raise ValueError(f"SHA-256 must be 64 hex characters, got {len(v)}")
        return v

    def to_csv_row(self) -> dict:
        """Flatten to a dict suitable for csv.DictWriter."""
        d = self.model_dump()
        # Flatten lists to pipe-separated strings for CSV compatibility
        d["secondary_domains"] = "|".join(d.get("secondary_domains") or [])
        # Serialize enums to their value
        for key, val in d.items():
            if isinstance(val, Enum):
                d[key] = val.value
        return d

    @classmethod
    def csv_fieldnames(cls) -> list[str]:
        """Return the ordered list of CSV column names."""
        return list(cls.model_fields.keys()) + []


class PageRecord(BaseModel):
    """Normalized output of any text extractor — one page of a document."""

    document_id: str
    page: int = Field(ge=1)
    section: Optional[str] = Field(default=None, description="Section number, e.g. '8', '42A'")
    heading: Optional[str] = Field(default=None, description="Section or heading title")
    text: str = Field(description="Extracted text content — never modified from source")
    source_url: Optional[str] = Field(default=None)
    legal_domain: str = Field(default=LegalDomain.UNCLASSIFIED.value)
    page_id: Optional[str] = Field(default=None, description="Unique page identifier")
    synthetic: bool = Field(default=False, description="Flag indicating synthetic test data")
    # OCR metadata
    ocr_used: bool = Field(default=False)
    ocr_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="OCR confidence normalized to 0.0-1.0")
    ocr_engine: Optional[str] = Field(default=None)
    ocr_language: Optional[str] = Field(default=None)
    extraction_method: ExtractionMethod = Field(default=ExtractionMethod.PDF_TEXT)
    word_count: Optional[int] = Field(default=None)

    @field_validator("ocr_confidence", mode="before")
    @classmethod
    def normalize_ocr_confidence(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            try:
                val = float(v)
                if 1.0 < val <= 100.0:
                    val = val / 100.0
                return val
            except (ValueError, TypeError):
                return None
        return None

    def model_post_init(self, __context) -> None:
        if self.word_count is None and self.text:
            self.word_count = len(self.text.split())


class SectionRecord(BaseModel):
    """A logical legal section extracted from a document."""

    section_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    version_group_id: Optional[str] = None
    version_id: Optional[str] = None
    title: Optional[str] = None
    domain: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    subsection: Optional[str] = None
    clause: Optional[str] = None
    act_id: Optional[str] = None
    section_number: str
    sub_section: Optional[str] = None
    heading: Optional[str] = None
    text: str
    provisions: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    source_authority: str = Field(default=SourceAuthority.PRIMARY_OFFICIAL.value)
    legal_domain: str = Field(default=LegalDomain.UNCLASSIFIED.value)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    synthetic: bool = Field(default=False)


class FailedDownload(BaseModel):
    """One row in legal-data/logs/failed_downloads.csv."""

    url: str
    source_id: str
    source_name: str
    reason: str
    http_status: Optional[int] = None
    error_type: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(default=0)
    recommended_action: Optional[str] = None


class SkippedSource(BaseModel):
    """One row in legal-data/logs/skipped_sources.csv."""

    url: str
    source_id: str
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    note: Optional[str] = None
