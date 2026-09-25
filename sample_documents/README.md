# Sample Legal Documents for LegalLens Testing

This directory contains realistic Indian legal documents in **PDF** and **TXT** formats. You can upload any of these files directly using the **Upload & Analyze Document** dropzone on the LegalLens Dashboard (`http://localhost:3000/dashboard`).

---

## Document Catalog

### 1. `Executive_Employment_Agreement.pdf`
- **Document Type**: Commercial Employment Agreement
- **Parties**: TechNova Solutions India Pvt. Ltd. & Mr. Arjun Sharma (VP of Engineering)
- **Key Clauses**:
  - **Termination**: 30 days written notice or 30 days basic salary in lieu.
  - **Non-Compete**: 24-month nationwide post-termination non-compete restraint.
- **Recommended AI Tasks**:
  - **Clause Intelligence**: Observe LegalLens flag the 24-month non-compete covenant as **void under Section 27 of the Indian Contract Act, 1872**.
  - **Party Obligations**: Extracts covenants for both Executive and Company.
  - **Deadlines**: Identifies 30-day notice and 3-year confidentiality survival.

---

### 2. `Commercial_Lease_Agreement_Mumbai.pdf`
- **Document Type**: Commercial Lease and License Agreement
- **Parties**: Premier Realty Holdings Ltd. & Zenith Data Analytics India Pvt. Ltd.
- **Premises**: Bandra Kurla Complex (BKC), Mumbai, Maharashtra.
- **Key Clauses**:
  - **Term**: 36 months.
  - **Lock-in Period**: Mandatory 12-month lock-in period with full rent liability upon early exit.
  - **Security Deposit**: INR 15,00,000 (6 months rent), refundable within 15 days of handover.
  - **Default**: 15 days written cure notice before lease termination.
- **Recommended AI Tasks**:
  - **Deadlines**: Extract 12-month lock-in, 15-day refund timeline, and 15-day cure period.
  - **Obligations**: Financial and maintenance covenants of Lessor and Lessee.

---

### 3. `Mutual_Non_Disclosure_Agreement.pdf`
- **Document Type**: Mutual Non-Disclosure Agreement (NDA)
- **Parties**: Bharat FinTech Innovations LLP & Delta Cyber Security Pvt. Ltd.
- **Key Clauses**:
  - **Return of Materials**: Mandatory return or destruction within 7 business days of written notice.
  - **Survival**: Confidentiality survives for 5 years.
  - **Jurisdiction**: Exclusive jurisdiction of New Delhi courts.
- **Recommended AI Tasks**:
  - **Executive Summary**: Overview of proprietary data definitions and exclusions.
  - **Deadlines**: Identifies the 7-day material return deadline and 5-year survival term.

---

### 4. `Master_Software_Services_Contract.pdf`
- **Document Type**: Master Services & Cloud SLA Contract
- **Parties**: Apex Digital Enterprises Ltd. & CloudSphere Technologies India Pvt. Ltd.
- **Key Clauses**:
  - **SLA**: 99.9% uptime commitment with tiered service credits.
  - **Payment**: 30 days net from invoice date.
  - **Limitation of Liability**: Capped at aggregate 12-month trailing fees.
  - **Audit Rights**: Once annually with 14 days prior notice.
- **Recommended AI Tasks**:
  - **Compare Tool**: Compare against another draft to assess shifted SLA thresholds.
  - **Obligations**: Extracts uptime and audit covenants.

---

### 5. `Consumer_Dispute_Legal_Notice.pdf`
- **Document Type**: Advocate's Statutory Legal Notice
- **Statute**: Consumer Protection Act, 2019 (Section 35)
- **Parties**: Complainant Vivek Sen via Advocate Rajesh K. Varma vs. Global FastTrack Logistics India Pvt. Ltd.
- **Key Clauses**:
  - **Loss of Consignment**: Claim for INR 4,80,000 + INR 1,00,000 mental agony.
  - **Notice Period**: 15 days to comply before consumer commission filing.
- **Recommended AI Tasks**:
  - **Ask LegalLens**: Query statutory cause of action and 15-day cure window.
  - **Lawyer Handoff Dossier**: Export structured advocate summary.
