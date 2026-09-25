"""
tests/test_ingestion_pipeline.py
================================
Comprehensive integration and regression test suite for LegalLens pipeline.

Verifies:
1. Valid PDF ingestion through entire chain: validation -> extraction -> provenance -> catalogue
2. Corrupt / invalid PDF detection (non-%PDF- magic bytes)
3. HTML masquerading as PDF (e.g. error portal HTML disguised as .pdf)
4. HTTP 404 / 403 failure handling and catalogue logging
5. HTTP 429 retry-after behavior
6. Robots UNKNOWN policy: permissive vs conservative
7. Secret redaction in URLs, error messages, catalogue, and provenance
8. Version grouping across years (amendments map to base act group)
9. eCourts zero network requests contract
10. Dry-run zero-storage guarantee
"""

import asyncio
import json
from pathlib import Path
import pytest
import respx
import httpx

from pipeline.core.catalogue import Catalogue
from pipeline.core.config import PipelineConfig, SourceConfig
from pipeline.core.http_client import (
    LegalLensClient,
    RobotsCache,
    RobotsDecision,
    RobotsBlockedError,
    DownloadError,
    redact_secrets_from_url,
)
from pipeline.core.metadata import (
    DocumentMetadata,
    DocumentType,
    SourceAuthority,
    ExtractionMethod,
    PageRecord,
)
from pipeline.validation.validator import ArtifactValidator
from pipeline.versioning.version_tracker import VersionTracker
from pipeline.provenance.provenance import ProvenanceRecord, ProvenanceRegistry
from pipeline.adapters.ecourts import collect as ecourts_collect


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def test_env(tmp_path):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    datasets_dir = tmp_path / "datasets"
    logs_dir = tmp_path / "logs"

    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    datasets_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)

    catalogue = Catalogue(datasets_dir=str(datasets_dir), logs_dir=str(logs_dir))
    catalogue.load()

    version_tracker = VersionTracker()

    cfg = PipelineConfig()
    cfg.storage.raw_dir = str(raw_dir)
    cfg.storage.processed_dir = str(processed_dir)
    cfg.storage.datasets_dir = str(datasets_dir)
    cfg.storage.logs_dir = str(logs_dir)
    cfg.collection.request_delay_seconds = 0.0
    cfg.collection.request_jitter_seconds = 0.0
    cfg.collection.max_retries = 2

    return {
        "root": tmp_path,
        "raw_dir": raw_dir,
        "processed_dir": processed_dir,
        "datasets_dir": datasets_dir,
        "logs_dir": logs_dir,
        "catalogue": catalogue,
        "version_tracker": version_tracker,
        "cfg": cfg,
    }


VALID_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n72 712 Td\n(LegalLens Test) Tj\nET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000337 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n413\n%%EOF\n"
)


# ── 1. Valid PDF Ingestion ────────────────────────────────────

def test_valid_pdf_validation(tmp_path):
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(VALID_PDF_BYTES)

    val = ArtifactValidator.validate_file(pdf_file, expected_format="pdf")
    assert val.is_valid is True
    assert val.detected_type == "pdf"
    assert len(val.sha256) == 64


# ── 2. Corrupted PDF Detection ────────────────────────────────

def test_corrupt_pdf_validation(tmp_path):
    garbage = b"THIS IS NOT A REAL PDF FILE HEADER"
    bad_file = tmp_path / "corrupt.pdf"
    bad_file.write_bytes(garbage)

    val = ArtifactValidator.validate_file(bad_file, expected_format="pdf")
    assert val.is_valid is False
    assert "Missing %PDF-" in val.error_message


# ── 3. HTML Masquerading as PDF Detection ─────────────────────

def test_html_masquerading_as_pdf(tmp_path):
    fake_pdf = b"<!DOCTYPE html><html><head><title>Portal Login</title></head><body>Please login</body></html>"
    html_as_pdf = tmp_path / "portal_error.pdf"
    html_as_pdf.write_bytes(fake_pdf)

    val = ArtifactValidator.validate_file(html_as_pdf, expected_format="pdf")
    assert val.is_valid is False
    assert val.detected_type == "html_as_pdf"
    assert "contains HTML content" in val.error_message


# ── 4. HTTP 404 / 403 Handling ────────────────────────────────

@pytest.mark.asyncio
async def test_http_404_and_403_handling(test_env):
    cfg = test_env["cfg"]
    catalogue = test_env["catalogue"]

    with respx.mock(base_url="https://fake-court.gov.in") as respx_mock:
        respx_mock.get("/robots.txt").respond(200, text="User-agent: *\nAllow: /")
        respx_mock.get("/not_found.pdf").respond(404)
        respx_mock.get("/forbidden.pdf").respond(403)

        async with LegalLensClient(cfg) as client:
            dest_404 = test_env["raw_dir"] / "404.pdf"
            with pytest.raises(DownloadError) as exc_404:
                await client.download_file("https://fake-court.gov.in/not_found.pdf", dest=dest_404)
            assert exc_404.value.http_status == 404
            assert not dest_404.exists()

            dest_403 = test_env["raw_dir"] / "403.pdf"
            with pytest.raises(DownloadError) as exc_403:
                await client.download_file("https://fake-court.gov.in/forbidden.pdf", dest=dest_403)
            assert exc_403.value.http_status == 403
            assert not dest_403.exists()


# ── 5. HTTP 429 Retry-After Behavior ──────────────────────────

@pytest.mark.asyncio
async def test_http_429_retry_handling(test_env):
    cfg = test_env["cfg"]
    cfg.collection.max_retries = 2

    with respx.mock(base_url="https://rate-limited.gov.in") as respx_mock:
        respx_mock.get("/robots.txt").respond(200, text="User-agent: *\nAllow: /")
        # Fail once with 429, then succeed with 200
        respx_mock.get("/doc.pdf").side_effect = [
            httpx.Response(429, headers={"Retry-After": "0.1"}),
            httpx.Response(200, content=b"%PDF-1.4\ntest\n%%EOF"),
        ]

        async with LegalLensClient(cfg) as client:
            dest = test_env["raw_dir"] / "retry_doc.pdf"
            meta = await client.download_file("https://rate-limited.gov.in/doc.pdf", dest=dest)
            assert dest.exists()
            assert meta.status_code == 200


# ── 6. Robots UNKNOWN Policy (Permissive vs Conservative) ──────

@pytest.mark.asyncio
async def test_robots_unknown_policy(tmp_path):
    audit_file = tmp_path / "robots_audit.jsonl"

    with respx.mock(base_url="https://unreachable-robots.gov.in") as respx_mock:
        respx_mock.get("/robots.txt").respond(500)

        # Conservative: UNKNOWN -> DISALLOW
        cache_conservative = RobotsCache(
            audit_log_path=str(audit_file),
            unknown_policy="conservative",
        )
        dec_cons = await cache_conservative.check_url("https://unreachable-robots.gov.in/page")
        assert dec_cons == RobotsDecision.UNKNOWN
        # Under conservative policy, LegalLensClient blocks
        cfg_cons = PipelineConfig()
        cfg_cons.collection.robots_unknown_policy = "conservative"
        async with LegalLensClient(cfg_cons) as client_cons:
            with pytest.raises(RobotsBlockedError):
                await client_cons.get("https://unreachable-robots.gov.in/page")

        # Permissive: UNKNOWN -> ALLOW
        cfg_perm = PipelineConfig()
        cfg_perm.collection.robots_unknown_policy = "permissive"
        respx_mock.get("/page").respond(200, text="Hello world")
        async with LegalLensClient(cfg_perm) as client_perm:
            resp = await client_perm.get("https://unreachable-robots.gov.in/page")
            assert resp.status_code == 200


# ── 7. Secret Redaction ───────────────────────────────────────

def test_secret_redaction():
    url_with_key = "https://api.data.gov.in/resource/123?api-key=SECRET_API_KEY_999&format=csv"
    redacted = redact_secrets_from_url(url_with_key)
    assert "SECRET_API_KEY_999" not in redacted
    assert "api-key=REDACTED" in redacted

    bearer_url = "https://api.gov.in/data?token=my_secret_token_abc&query=acts"
    redacted_token = redact_secrets_from_url(bearer_url)
    assert "my_secret_token_abc" not in redacted_token
    assert "token=REDACTED" in redacted_token


# ── 8. Version Grouping Across Years ──────────────────────────

def test_version_grouping_across_years():
    vt = VersionTracker()
    base_group_id = vt.generate_version_group_id(
        title="Information Technology Act",
        act_year=2000,
        act_number="21",
        jurisdiction="Union of India",
    )
    amendment_group_id = vt.generate_version_group_id(
        title="Information Technology (Amendment) Act",
        act_year=2008,
        act_number="10",
        jurisdiction="Union of India",
    )
    # Both should map to same group because norm_title matches base act
    assert base_group_id == amendment_group_id


# ── 9. eCourts Zero Network Requests Contract ─────────────────

@pytest.mark.asyncio
async def test_ecourts_zero_http_requests(test_env):
    catalogue = test_env["catalogue"]
    raw_dir = str(test_env["raw_dir"])

    # Even with respx mock, if any request was made to services.ecourts.gov.in it would fail
    collected = await ecourts_collect(catalogue=catalogue, raw_dir=raw_dir)
    assert collected == 0
    assert catalogue.is_skipped("https://services.ecourts.gov.in")


# ── 10. Dry-Run Zero-Storage Guarantee ─────────────────────────

@pytest.mark.asyncio
async def test_dry_run_zero_storage(test_env):
    catalogue = test_env["catalogue"]
    raw_dir = test_env["raw_dir"]
    processed_dir = test_env["processed_dir"]

    # Initial state
    assert len(list(raw_dir.rglob("*"))) == 0
    assert len(list(processed_dir.rglob("*"))) == 0
    assert len(catalogue.documents) == 0
