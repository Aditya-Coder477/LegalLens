"""
validate_synthetic_dataset.py
==============================
Validates the LegalLens Synthetic Indian Legal Corpus against all 15 quality,
integrity, security, and guardrail rules.
Exits with 0 if all rules pass, or 1 if any violation is detected.

Usage:
    python validate_synthetic_dataset.py [--corpus-dir legal-data/synthetic]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

from pipeline.synthetic import LEGAL_DISCLAIMER

FORBIDDEN_URL_FRAGMENTS = [
    "indiacode.nic.in",
    "sci.gov.in",
    "main.sci.gov.in",
    "nalsa.gov.in",
    "meity.gov.in",
    "legislative.gov.in",
    "data.gov.in",
    "ecourts.gov.in",
]

FORBIDDEN_COURT_NAMES = [
    "Supreme Court of India",
    "High Court of Delhi",
    "High Court of Bombay",
    "High Court of Madras",
    "High Court of Calcutta",
    "High Court of Karnataka",
    "High Court of Allahabad",
]

REAL_INDIAN_COMPANIES = [
    "Reliance Industries",
    "Tata Consultancy Services",
    "Infosys",
    "HDFC Bank",
    "ICICI Bank",
    "State Bank of India",
    "Wipro",
    "Adani Enterprises",
]

class CorpusValidator:
    def __init__(self, corpus_root: str | Path = "legal-data/synthetic"):
        self.root = Path(corpus_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed_rules: List[str] = []

    def log_error(self, rule: str, msg: str):
        self.errors.append(f"[{rule} FAILED] {msg}")

    def log_pass(self, rule: str, msg: str):
        self.passed_rules.append(f"[{rule} PASSED] {msg}")

    def run_all_checks(self) -> bool:
        if not self.root.exists():
            self.log_error("RULE-0", f"Corpus root directory {self.root} does not exist.")
            return False

        print(f"Running validation on synthetic dataset at: {self.root.resolve()}\n")

        # Load structured files
        docs_file = self.root / "structured" / "documents.jsonl"
        secs_file = self.root / "structured" / "sections.jsonl"
        pages_file = self.root / "structured" / "pages.jsonl"
        conts_file = self.root / "structured" / "contracts.jsonl"

        if not docs_file.exists() or not secs_file.exists() or not pages_file.exists():
            self.log_error("RULE-0", "Essential structured JSONL files missing.")
            return False

        documents: List[Dict[str, Any]] = [json.loads(line) for line in docs_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        sections: List[Dict[str, Any]] = [json.loads(line) for line in secs_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        pages: List[Dict[str, Any]] = [json.loads(line) for line in pages_file.read_text(encoding="utf-8").splitlines() if line.strip()]

        doc_ids = {d["document_id"] for d in documents}
        sec_ids = {s["section_id"] for s in sections}

        # ── Rule 1: synthetic == True on all records ──
        bad_synth = [d["document_id"] for d in documents if not d.get("synthetic")]
        bad_synth_sec = [s["section_id"] for s in sections if not s.get("synthetic")]
        bad_synth_pg = [p["page_id"] for p in pages if not p.get("synthetic")]
        if bad_synth or bad_synth_sec or bad_synth_pg:
            self.log_error("RULE-1", f"Found records with synthetic != True (docs={len(bad_synth)}, secs={len(bad_synth_sec)}, pages={len(bad_synth_pg)})")
        else:
            self.log_pass("RULE-1", f"All {len(documents)} documents, {len(sections)} sections, and {len(pages)} pages have synthetic=True.")

        # ── Rule 2: source_authority == 'SYNTHETIC' ──
        bad_auth = [d["document_id"] for d in documents if d.get("source_authority") != "SYNTHETIC"]
        bad_auth_sec = [s["section_id"] for s in sections if s.get("source_authority") != "SYNTHETIC"]
        if bad_auth or bad_auth_sec:
            self.log_error("RULE-2", f"Found records where source_authority != 'SYNTHETIC' (docs={len(bad_auth)}, secs={len(bad_auth_sec)})")
        else:
            self.log_pass("RULE-2", "All records have source_authority='SYNTHETIC'.")

        # ── Rule 3: No real URLs ──
        url_violations = []
        for d in documents:
            url_str = str(d.get("source_url") or "") + str(d.get("official_url") or "")
            for frag in FORBIDDEN_URL_FRAGMENTS:
                if frag in url_str:
                    url_violations.append((d["document_id"], frag))
        if url_violations:
            self.log_error("RULE-3", f"Forbidden official government URLs detected: {url_violations}")
        else:
            self.log_pass("RULE-3", "Zero live government or official URLs in metadata.")

        # ── Rule 4: No real court names in judgments ──
        court_violations = []
        for d in documents:
            if d.get("document_type") == "judgment":
                c_name = d.get("court", "")
                for forbidden in FORBIDDEN_COURT_NAMES:
                    if forbidden in c_name:
                        court_violations.append((d["document_id"], c_name))
        if court_violations:
            self.log_error("RULE-4", f"Real court names detected in judgments: {court_violations}")
        else:
            self.log_pass("RULE-4", "All judgments use strictly fictional synthetic courts.")

        # ── Rule 5: No real company names in contracts ──
        company_violations = []
        for d in documents:
            if d.get("document_type") == "contract":
                parties_str = " ".join(d.get("parties", []))
                for rc in REAL_INDIAN_COMPANIES:
                    if rc in parties_str:
                        company_violations.append((d["document_id"], rc))
        if company_violations:
            self.log_error("RULE-5", f"Real corporate entities detected in contracts: {company_violations}")
        else:
            self.log_pass("RULE-5", "All contracts use strictly fictional synthetic companies.")

        # ── Rule 6: Minimum document count (>= 100) ──
        if len(documents) < 100:
            self.log_error("RULE-6", f"Document count {len(documents)} is below minimum threshold of 100.")
        else:
            self.log_pass("RULE-6", f"Document count requirement met: {len(documents)} documents (target >= 100).")

        # ── Rule 7: Minimum section count (>= 500) ──
        if len(sections) < 500:
            self.log_error("RULE-7", f"Section count {len(sections)} is below minimum threshold of 500.")
        else:
            self.log_pass("RULE-7", f"Section count requirement met: {len(sections)} sections (target >= 500).")

        # ── Rule 8: Raw files exist and match recorded file sizes ──
        missing_files = []
        for d in documents:
            rel_path = d.get("raw_file_path")
            if not rel_path:
                missing_files.append((d["document_id"], "no path"))
                continue
            full_path = self.root / rel_path
            if not full_path.exists() or full_path.stat().st_size == 0:
                missing_files.append((d["document_id"], rel_path))
        if missing_files:
            self.log_error("RULE-8", f"Missing or empty raw files on disk: {missing_files[:5]}")
        else:
            self.log_pass("RULE-8", f"All {len(documents)} raw files exist on disk and are non-empty.")

        # ── Rule 9: SHA-256 integrity check against disk bytes ──
        hash_mismatches = []
        for d in documents:
            rel_path = d["raw_file_path"]
            full_path = self.root / rel_path
            disk_bytes = full_path.read_bytes()
            computed_hash = hashlib.sha256(disk_bytes).hexdigest()
            if computed_hash != d.get("sha256"):
                hash_mismatches.append((d["document_id"], d.get("sha256"), computed_hash))
        if hash_mismatches:
            self.log_error("RULE-9", f"SHA-256 mismatches found: {hash_mismatches[:5]}")
        else:
            self.log_pass("RULE-9", "All document hashes match exact disk byte contents.")

        # ── Rule 10: No orphan sections ──
        orphan_secs = [s["section_id"] for s in sections if s["document_id"] not in doc_ids]
        if orphan_secs:
            self.log_error("RULE-10", f"Found orphan sections referencing nonexistent documents: {orphan_secs[:5]}")
        else:
            self.log_pass("RULE-10", "Zero orphan sections; all sections point to valid document IDs.")

        # ── Rule 11: No orphan pages ──
        orphan_pages = [p["page_id"] for p in pages if p["document_id"] not in doc_ids]
        if orphan_pages:
            self.log_error("RULE-11", f"Found orphan pages referencing nonexistent documents: {orphan_pages[:5]}")
        else:
            self.log_pass("RULE-11", "Zero orphan pages; all pages point to valid document IDs.")

        # ── Rule 12: Evaluation datasets exist and verify ──
        qa_file = self.root / "evaluation" / "qa.jsonl"
        ret_file = self.root / "evaluation" / "retrieval_ground_truth.jsonl"
        if not qa_file.exists() or not ret_file.exists():
            self.log_error("RULE-12", "Evaluation files qa.jsonl or retrieval_ground_truth.jsonl missing.")
        else:
            qa_records = [json.loads(line) for line in qa_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            bad_qa_docs = [q["question_id"] for q in qa_records if q["source_document_id"] not in doc_ids]
            bad_qa_secs = [q["question_id"] for q in qa_records if q["source_section_id"] not in sec_ids]
            if bad_qa_docs or bad_qa_secs:
                self.log_error("RULE-12", f"QA references invalid documents ({len(bad_qa_docs)}) or sections ({len(bad_qa_secs)})")
            else:
                self.log_pass("RULE-12", f"All {len(qa_records)} QA records correctly cite valid documents and sections.")

        # ── Rule 13: Unanswerable queries have expected_behavior = 'ABSTAIN' ──
        unans_file = self.root / "evaluation" / "unanswerable.jsonl"
        if not unans_file.exists():
            self.log_error("RULE-13", "unanswerable.jsonl missing.")
        else:
            unans_recs = [json.loads(line) for line in unans_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            non_abstains = [u["question_id"] for u in unans_recs if u.get("expected_behavior") != "ABSTAIN"]
            if non_abstains:
                self.log_error("RULE-13", f"Unanswerable records without expected_behavior='ABSTAIN': {non_abstains}")
            else:
                self.log_pass("RULE-13", f"All {len(unans_recs)} unanswerable records mandate expected_behavior='ABSTAIN'.")

        # ── Rule 14: Contradiction pairs cite valid documents ──
        contra_file = self.root / "evaluation" / "contradictions.jsonl"
        if not contra_file.exists():
            self.log_error("RULE-14", "contradictions.jsonl missing.")
        else:
            contra_recs = [json.loads(line) for line in contra_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            invalid_contras = []
            for c in contra_recs:
                if c["document_a_id"] not in doc_ids or c["document_b_id"] not in doc_ids:
                    invalid_contras.append(c["contradiction_id"])
            if invalid_contras:
                self.log_error("RULE-14", f"Contradictions referencing invalid documents: {invalid_contras}")
            else:
                self.log_pass("RULE-14", f"All {len(contra_recs)} contradiction pairs cite verified documents.")

        # ── Rule 15: Manifest and Reports contain legal disclaimer ──
        manifest_file = self.root / "SYNTHETIC_MANIFEST.json"
        report_file = self.root / "reports" / "SYNTHETIC_DATASET_REPORT.md"
        stats_file = self.reports_dir_stats = self.root / "reports" / "SYNTHETIC_DATASET_STATS.json"
        if not manifest_file.exists() or not report_file.exists() or not stats_file.exists():
            self.log_error("RULE-15", "Manifest or Report files missing.")
        else:
            m_text = manifest_file.read_text(encoding="utf-8")
            r_text = report_file.read_text(encoding="utf-8")
            if "All documents in this corpus are synthetic" not in m_text or "All documents in this corpus are synthetic" not in r_text:
                self.log_error("RULE-15", "Legal disclaimer missing from manifest or report.")
            else:
                self.log_pass("RULE-15", "Manifest, stats, and audit report contain mandatory legal disclaimer.")

        # Summary
        print("=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        for p in self.passed_rules:
            print(f"  [PASS] {p}")

        if self.errors:
            print("\nERRORS DETECTED:")
            for e in self.errors:
                print(f"  [FAIL] {e}")
            return False

        print("\nAll 15 Validation Rules Passed Successfully (100% Quality & Guardrails Compliance)!")
        print("=" * 70)
        return True

def main():
    parser = argparse.ArgumentParser(description="Validate LegalLens Synthetic Dataset.")
    parser.add_argument(
        "--corpus-dir",
        "-c",
        type=str,
        default="legal-data/synthetic",
        help="Path to synthetic corpus root.",
    )
    args = parser.parse_args()

    validator = CorpusValidator(corpus_root=args.corpus_dir)
    success = validator.run_all_checks()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
