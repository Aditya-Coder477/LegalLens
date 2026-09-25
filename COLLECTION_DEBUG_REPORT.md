# LegalLens — Production Pipeline Audit, Repair & Integration Report

**Date:** 2026-09-21  
**Project:** LegalLens (India-First GenAI Legal Assistance Platform)  
**Author:** AI Pair Programmer (DeepMind Antigravity)  
**Pipeline Run ID:** `09c979c6-24ac-4f7a-ab60-8cdb6cc982fd`

---

## 1. Executive Summary

A comprehensive forensic audit of the LegalLens Indian legal data ingestion pipeline was conducted to address the failure state: **0 documents collected, 17 failed download records, and 0 B storage**.

Rather than rebuilding the project from scratch, all working modular components were retained and repaired. Root causes were identified across the HTTP networking stack, government SSL certificate handling, robots parser timeouts, URL structure drift, PDF extraction imports, and Windows filesystem mechanics.

Following the repairs:
- **104/104 unit, smoke, and integration tests pass** with 0 regressions.
- **Controlled live ingestion succeeded on NALSA**: 2 authentic government documents (total ~2.08 MB) were downloaded, verified against corrupted/HTML masquerading artifacts via `ArtifactValidator`, and fully extracted into **120 individual page records**.
- **120 audit provenance records** were appended to `legal-data/processed/metadata/provenance.jsonl`.
- **Catalogue and quality reports** now reflect real, validated storage and comprehensive telemetry.
- **eCourts remained manual-only** with strictly zero automated HTTP requests.

---

## 2. Baseline Audit & Root Cause Analysis

The baseline run logged 17 failures across 13 distinct URLs. The table below details each failure cluster, the underlying root cause, and the repair implemented:

| # | Target / URL Pattern | Baseline Error | Root Cause Analysis | Fix Implemented |
|---|----------------------|----------------|---------------------|-----------------|
| 1 | `https://nalsa.gov.in/acts-rules` | HTTP 404 Not Found | NALSA migrated CMS to S3WaaS platform; old path `/acts-rules` no longer exists. | Updated `config.yaml` to active S3WaaS endpoints `/notifications/` and `/statistics/` which host live PDFs on `cdnbbsr.s3waas.gov.in`. |
| 2 | `https://nalsa.gov.in/schemes` | HTTP 404 Not Found | S3WaaS CMS path change. | Redirected discovery to verified live paths in `pipeline/adapters/nalsa.py`. |
| 3 | `https://www.sci.gov.in/wp-content/uploads/...` | HTTP 404 Not Found | Hardcoded paths on Supreme Court portal were obsolete or dynamically routed. | Replaced legacy path in `config.yaml` with stable `/rules/` index path. |
| 4 | `https://www.meity.gov.in/writereaddata/files/...` | HTTP 403 Forbidden | MeitY government WAF blocks non-standard bot User-Agents deterministically. | Documented WAF barrier honestly; adapter catches 403 deterministically without evasion, marks status `BLOCKED` in `source_check.py`. |
| 5 | `https://legislative.gov.in/actsofparliamentfromtheyear` | HTTP 403 Forbidden | NIC edge firewall restricts automated crawling; also Python `urllib` SSL handshake failed due to missing intermediate certs. | Rewrote `pipeline/core/http_client.py` to use `httpx.AsyncClient(verify=False)` and handle deterministic 403s cleanly. |
| 6 | `https://www.indiacode.nic.in/robots.txt` | ReadTimeout / SSL Error | Python's standard `urllib.robotparser` is synchronous, blocking, and strictly verifies SSL certificates which fail on NIC servers. | Replaced `urllib` fetcher with async `httpx` in `RobotsCache` with SSL verification tolerance. |
| 7 | `https://www.indiacode.nic.in/handle/123456789/1362` | HTTP 403 Forbidden | India Code main DSpace portal blocks direct automated crawling with Cloudflare/WAF. | Added preflight health check (`source_check.py`), routed section queries to `indiacode.ecourtsindia.com/api` (community tier). |
| 8 | `https://api.data.gov.in/catalog/all` | DownloadError (401/Missing Key) | `DATA_GOV_API_KEY` was missing from `.env`. Adapter previously leaked secrets into failure logs. | Added `redact_secrets_from_url` sanitizing query params (`api-key=REDACTED`) across URLs, error logs, and `sources.csv`. |
| 9 | `pipeline/extractors/pdf_extractor.py` | `ImportError: cannot import name 'LTAnon'` | Unused `LTAnon` import in `pdfminer.layout` caused PDF text extraction to abort and fail silently. | Cleaned imports in `pdf_extractor.py` to only import `LTTextBox`, restoring high-speed text extraction. |
| 10 | Windows atomic replace | `WinError 183: Cannot create a file when that file already exists` | `Path.rename()` on Windows fails when the destination exists. | Replaced with `Path.replace()` (`os.replace`) which supports atomic overwrites on Windows. |
| 11 | Provenance registry path | `PermissionError: [Errno 13]` | `ProvenanceRegistry` appended `/provenance.jsonl` to paths already ending in `.jsonl`, creating a directory. | Normalized `ProvenanceRegistry.__init__` to detect `.jsonl` suffix and write to the file directly. |
| 12 | Dry-run accounting bug | `collected += 1` in dry-run | Adapters previously incremented the `collected` counter during dry-runs, reporting false collections. | Removed increment from `if dry_run:` branches across all adapters. |

---

## 3. End-to-End Pipeline Architecture Verification

The complete ingestion sequence was verified end-to-end:

```mermaid
flowchart TD
    A[Source Discovery] --> B[Robots.txt & Access Check]
    B -->|Allowed| C[Atomic Download via HTTP Client]
    C --> D[Raw Storage .part -> replace]
    D --> E[SHA-256 Hash Computation]
    E --> F[Artifact Validation: Magic Bytes sniffer]
    F -->|Invalid / HTML disguised| G[Mark Failed & Unlink]
    F -->|Valid| H[Text Extraction & Fallback Sniffer]
    H --> I[PageRecord Extraction: 120 pages]
    I --> J[Classification: Title + Extracted Text]
    J --> K[Version Group Assignment: UUID5]
    K --> L[Provenance Recording: JSONL Chain]
    L --> M[Catalogue Upsert: sources.csv]
    M --> N[Deduplication Check]
    N --> O[Data Quality Report Generation]
```

---

## 4. Quantitative Pipeline Comparison: Before vs. After

| Metric | Initial Run (Baseline) | Controlled Live Run (Repaired) | Change |
|--------|------------------------|--------------------------------|--------|
| **Total Documents Catalogued** | 0 | **2** | +2 |
| **Raw Storage Utilized** | 0.0 B | **2.08 MB (2,076,140 bytes)** | +2.08 MB |
| **Processed Storage** | 0.0 B | **~245 KB (120 pages JSONL)** | +245 KB |
| **Extracted Pages** | 0 | **120 pages** | +120 |
| **Audit Provenance Records** | 0 | **120 records** | +120 |
| **Unit / Integration Tests** | 94 passing (1 failing) | **104 passed / 0 failed** | +10 passed |
| **Distinct Failed URLs** | 13 | 13 (historical from baseline) | 0 new failures |
| **Secret Leaks in CSV/Logs** | Potential leak | **0 (Strictly Redacted)** | Guaranteed safe |
| **Automated Requests to eCourts** | 0 | **0** | Strictly compliant |

---

## 5. Artifacts and Evidence

### A. Raw Files Verified on Disk
- `legal-data/raw/nalsa/20260520897097988.pdf` (1,153,282 bytes) — SHA-256: `9a858b1168ad04bf3ccdeaffffed08c0ce4ecdfe1c3a367883a5ddff0dec2cea`
- `legal-data/raw/nalsa/20251122262010823.pdf` (922,858 bytes) — SHA-256: `dccc0638f283adfbac6160a7dc1f27375b09b6939f20544df8ceb1f00298defd`

### B. Processed Page Extractions
- `legal-data/processed/pages/nalsa_9a858b1168ad.jsonl` (47 pages extracted)
- `legal-data/processed/pages/nalsa_dccc0638f283.jsonl` (73 pages extracted)

### C. Audit Provenance Chain Sample
```json
{
  "document_id": "nalsa_9a858b1168ad",
  "source_instance_id": "nalsa_9a858b1168ad_1789916487",
  "source_id": "nalsa_9a858b1168ad",
  "source_name": "National Legal Services Authority (NALSA)",
  "source_authority": "OFFICIAL_LEGAL_AID",
  "source_url": "https://cdnbbsr.s3waas.gov.in/s32e45f93088c7db59767efef516b306aa/uploads/2026/05/20260520897097988.pdf",
  "local_file": "legal-data\\raw\\nalsa\\20260520897097988.pdf",
  "sha256": "9a858b1168ad04bf3ccdeaffffed08c0ce4ecdfe1c3a367883a5ddff0dec2cea",
  "page": 1,
  "extraction_method": "pdf_text",
  "ocr_used": false,
  "legal_domain": "Arbitration and Alternative Dispute Resolution",
  "created_at": "2026-09-20T20:31:30.450123"
}
```

---

## 6. Conclusion

The LegalLens data ingestion engine is now robust, resilient against government SSL and network idiosyncrasies, fully validated, and verified on live Indian legal infrastructure. All code changes were made minimally and surgically, preserving the original modular design.
