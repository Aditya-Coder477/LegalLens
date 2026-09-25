# LegalLens — Source Health, Compliance & Preflight Diagnostic Report

**Date:** 2026-09-21  
**Project:** LegalLens (Automated Indian Legal Data Collection Pipeline)  
**Status:** Audited & Verified

---

## 1. Executive Overview

This report provides the authoritative accessibility status, compliance posture, and data-harvesting strategy for each Indian legal information source configured within LegalLens.

In accordance with strict ethical and legal compliance guidelines:
- **No CAPTCHAs, OTPs, or authentication barriers are bypassed.**
- **No anti-bot evasion, browser spoofing, or stealth scraping is used.**
- **Access controls (HTTP 403 / WAF blocks) are respected and logged deterministically.**
- **eCourts is strictly manual-import only.**

---

## 2. Source Health Matrix

| Source ID | Name | Authority Tier | Status | Robots Policy | Base HTTP | Live Strategy |
|-----------|------|----------------|--------|---------------|-----------|---------------|
| `nalsa` | National Legal Services Authority | `OFFICIAL_LEGAL_AID` | **READY** | ALLOW | 200 | Automated discovery via S3WaaS endpoints `/notifications/` & `/statistics/`; direct PDF ingestion from `cdnbbsr.s3waas.gov.in`. |
| `india_code_api` | India Code Community API | `SECONDARY_COMMUNITY` | **READY** | ALLOW | 200 | Automated REST queries to `https://indiacode.ecourtsindia.com/api/v1/search` & `/v1/{code}` for section-level text. |
| `ecourts` | eCourts Services | `OFFICIAL_COURT` | **MANUAL** | N/A | N/A | **Zero automated requests**. Manual import via `import_manual.py` following instructions in `MANUAL_INGESTION.md`. |
| `data_gov` | Open Government Data Platform | `OFFICIAL_GOVERNMENT` | **BLOCKED** | N/A | N/A | Requires `DATA_GOV_API_KEY` in `.env`. Free registration available at `https://data.gov.in/user/register`. |
| `india_code` | India Code (Official Portal) | `PRIMARY_OFFICIAL` | **BLOCKED** | DISALLOW | 403 | NIC WAF restricts direct bot traffic. Automated requests blocked. Seed via manual import or `india_code_api`. |
| `supreme_court` | Supreme Court of India | `OFFICIAL_COURT` | **BLOCKED** | DISALLOW | 403 | Main portal blocks bot traffic via WAF. Static rules accessible on S3WaaS CDN when linked; judgments require manual import. |
| `legislative_dept` | Legislative Department | `PRIMARY_OFFICIAL` | **BLOCKED** | UNKNOWN | 403 | NIC edge firewall restricts bot user agents. Offline manual imports recommended for historical bare acts. |
| `meity` | Ministry of Electronics & IT | `OFFICIAL_GOVERNMENT` | **BLOCKED** | DISALLOW | 403 | Government WAF returns 403 Forbidden to crawler user agents. IT Rules and amendments should be imported manually. |

---

## 3. Detailed Source Breakdown & Ingestion Protocols

### 3.1 National Legal Services Authority (`nalsa`) — READY
- **Base URL:** `https://nalsa.gov.in`
- **Robots Decision:** `ALLOW`
- **Active Endpoints:**
  - `https://nalsa.gov.in/notifications/`
  - `https://nalsa.gov.in/statistics/`
- **CDN Storage:** Documents reside on government S3WaaS CDNs (e.g. `cdnbbsr.s3waas.gov.in`).
- **Data Types:** Legal aid scheme reports, conference resolutions, legal literacy notifications, legal aid statistics.
- **Extraction:** Native digital PDF text extraction via `pdfminer.six` with inline fallback to OCR.
- **Telemetry:** Ingested 2 complete documents (120 pages extracted, 120 provenance records).

### 3.2 India Code API (`india_code_api`) — READY
- **Base URL:** `https://indiacode.ecourtsindia.com/api`
- **Robots Decision:** `ALLOW`
- **OpenAPI Specification:** `https://indiacode.ecourtsindia.com/api/v1/openapi.json`
- **Endpoints Used:**
  - `GET /api/v1/search?q={query}`
  - `GET /api/v1/{act_code}`
- **Format:** JSON structure containing preamble, chapters, sections, and markdown provisions.
- **Authority Note:** Tagged as `SECONDARY_COMMUNITY`. If discrepancies exist between this API and official gazette acts, official gazette takes precedence.

### 3.3 eCourts Services (`ecourts`) — MANUAL ONLY
- **Target URL:** `https://services.ecourts.gov.in/ecourtindia_v6/`
- **Status:** Strictly Manual Ingestion.
- **Zero Request Guarantee:** Verified by unit and integration tests (`tests/test_adapters_smoke.py::test_zero_http_requests`, `tests/test_ingestion_pipeline.py::test_ecourts_zero_http_requests`).
- **Rationale:** eCourts requires session binding and interactive image CAPTCHA on every case query.
- **Manual Import Workflow:**
  ```bash
  python import_manual.py path/to/court_record.pdf \
    --source ecourts \
    --doc-type judgment \
    --domain "Criminal Law" \
    --title "State v. Ramesh Kumar" \
    --url "https://services.ecourts.gov.in/..." \
    --date 2024-01-15
  ```

### 3.4 Open Government Data Platform (`data_gov`) — REQUIRES API KEY
- **Base URL:** `https://api.data.gov.in`
- **Status:** Requires API key configuration.
- **Security & Privacy:** Redaction filter guarantees API keys (`?api-key=...`) are scrubbed before writing to logs, `sources.csv`, or error trackers.
- **Activation:** Set `DATA_GOV_API_KEY=your_key_here` in `.env`.

### 3.5 WAF-Restricted Government Portals (`meity`, `legislative_dept`, `supreme_court`, `india_code`)
- **Observed Behavior:** Each of these domains returns HTTP 403 Forbidden to the pipeline's identified User-Agent (`LegalLens-DataPipeline/1.0`).
- **Policy Compliance:** The pipeline makes zero attempts to forge headers, cycle proxies, or bypass access controls.
- **Recommendation:** Bulk statutory compilations (such as historical gazettes or large act bundles) should be placed into `legal-data/manual_drop/` and catalogued using `import_manual.py`.

---

## 4. Operational Recommendations

1. **Scheduled Ingestion:** Run automated collection for `nalsa` and `india_code_api` on a weekly schedule.
2. **Preflight Health Checks:** Before executing bulk runs, run:
   ```bash
   python source_check.py
   ```
   to detect server maintenance or endpoint migrations.
3. **Data Quality Assurance:** After any manual or automated ingestion, always execute:
   ```bash
   python generate_report.py
   ```
   to inspect validation rates, missing metadata, duplicate groupings, and storage utilization.
