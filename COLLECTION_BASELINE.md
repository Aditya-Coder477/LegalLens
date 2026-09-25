# LegalLens — Collection Baseline Report

**Date:** 2026-09-21  
**Author:** Antigravity Audit & Repair System  
**Test Suite State:** 94 passed, 0 failed, 0 errors (93.19s)  
**Corpus State:** 0 documents collected, 0 B raw storage, 0 B processed storage  
**Logged Failures:** 17 records in `legal-data/logs/failed_downloads.csv` (13 unique URLs)

---

## 1. Baseline Summary

While all 94 mock-based unit and adapter tests pass, the real collection run yielded 0 collected documents. This proves the user's directive: **"Do not assume that passing mocked tests proves real collection works."**

### Key Metrics Before Fixes:
- **Total Catalogued Documents:** 0
- **Raw Storage:** 0 B
- **Processed Storage:** 0 B
- **Failure Records:** 17 records logged in `failed_downloads.csv`
- **Total Test Count:** 94 tests (100% passing on mocked HTTP / internal components)
- **Unit Test Coverage:** 50% overall statement coverage

---

## 2. Failure Analysis of the 17 Records

From `legal-data/logs/failed_downloads.csv`, the 17 failure entries break down into 3 source classes and 4 root causes:

| # | Source | URL | HTTP Status | Exception / Error Message | Failure Stage | Root Cause Category | Distinct? |
|---|--------|-----|-------------|---------------------------|---------------|---------------------|-----------|
| 1-2 | NALSA | `https://nalsa.gov.in/schemes-programmes` | 404 | Client error '404 Not Found' | Discovery (seed) | Deterministic 404 / Obsolete route | Yes |
| 3-4 | NALSA | `https://nalsa.gov.in/publications` | 404 | Client error '404 Not Found' | Discovery (seed) | Deterministic 404 / Obsolete route | Yes |
| 5-6 | NALSA | `https://nalsa.gov.in/acts-rules` | 404 | Client error '404 Not Found' | Discovery (seed) | Deterministic 404 / Obsolete route | Yes |
| 7-8 | NALSA | `https://nalsa.gov.in/loksabha-data` | 404 | Client error '404 Not Found' | Discovery (seed) | Deterministic 404 / Obsolete route | Yes |
| 9 | Legislative Dept | `https://legislative.gov.in/constitution-of-india/` | None | SSL: CERTIFICATE_VERIFY_FAILED → treated as robots disallowed | Robots check | SSL/Network + Robots tri-state flaw | Yes |
| 10 | Legislative Dept | `https://legislative.gov.in/central-acts/` | None | SSL: CERTIFICATE_VERIFY_FAILED → treated as robots disallowed | Robots check | SSL/Network + Robots tri-state flaw | Yes |
| 11 | Legislative Dept | `https://legislative.gov.in/ordinances/` | None | SSL: CERTIFICATE_VERIFY_FAILED → treated as robots disallowed | Robots check | SSL/Network + Robots tri-state flaw | Yes |
| 12 | Legislative Dept | `https://legislative.gov.in/amendment-acts/` | None | SSL: CERTIFICATE_VERIFY_FAILED → treated as robots disallowed | Robots check | SSL/Network + Robots tri-state flaw | Yes |
| 13 | MeitY | `https://www.meity.gov.in/content/acts-rules` | 403 | HTTP 403 Forbidden — possible WAF block | Discovery (seed) | 403/WAF + Obsolete route | Yes |
| 14 | MeitY | `https://www.meity.gov.in/content/notifications` | 403 | HTTP 403 Forbidden — possible WAF block | Discovery (seed) | 403/WAF + Obsolete route | Yes |
| 15 | MeitY | `https://www.meity.gov.in/content/circulars` | 403 | HTTP 403 Forbidden — possible WAF block | Discovery (seed) | 403/WAF + Obsolete route | Yes |
| 16 | MeitY | `https://www.meity.gov.in/content/policies` | 403 | HTTP 403 Forbidden — possible WAF block | Discovery (seed) | 403/WAF + Obsolete route | Yes |
| 17 | MeitY | `https://www.meity.gov.in/content/guidelines` | 403 | HTTP 403 Forbidden — possible WAF block | Discovery (seed) | 403/WAF + Obsolete route | Yes |

---

## 3. Root Cause Grouping

1. **Obsolete Discovery Seed Paths (NALSA & MeitY):**
   - NALSA paths like `/schemes-programmes` and `/publications` are 404s on the live S3WaaS site. NALSA's current site uses different public paths.
   - MeitY paths under `/content/*` trigger immediate WAF 403 blocks or no longer exist.
2. **Robots.txt Tri-State Flaw (Legislative Dept):**
   - `urllib.robotparser` SSL failure while fetching `robots.txt` resulted in an empty parser or default block, falsely raising `RobotsBlockedError` on valid public paths.
3. **Flawed Download Accounting:**
   - In dry-run mode, discovered links were incremented as collected documents even though nothing was downloaded or validated.
4. **Disconnection Between Download and Text Extraction:**
   - In live collection, successful downloads were catalogued, but text extraction, OCR, classification from excerpt, and provenance creation were never executed automatically.
