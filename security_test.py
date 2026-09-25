"""
security_test.py
================
Dedicated Security & Adversarial Red-Teaming CLI for LegalLens Phase 8.
Runs targeted security test suites across:
- Direct & Indirect Prompt Injection
- Jailbreaks & Roleplay Bypass
- Canary Secret & System Prompt Leakage
- PII Leakage (Aadhaar, PAN, phone)
- Multi-Tenant & Document Isolation
- Malformed & Oversized Inputs
- Citation & Provenance Tampering

Usage:
  python security_test.py --all
  python security_test.py --prompt-injection
  python security_test.py --jailbreak
  python security_test.py --secrets
  python security_test.py --pii
  python security_test.py --tenant-isolation
  python security_test.py --file-security
  python security_test.py --provenance
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from pipeline.evaluation.config import get_evaluation_config
from pipeline.evaluation.models import EvaluationCase, SecurityFinding, SecuritySeverity
from pipeline.evaluation.reporter import EvaluationReporter
from pipeline.evaluation.safety_evaluator import SafetyEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("legallens.security_test")


def load_security_cases(data_dir: Path, target_categories: List[str]) -> List[EvaluationCase]:
    cases: List[EvaluationCase] = []
    for cat in target_categories:
        cat_file = data_dir / "security" / f"{cat}.jsonl"
        if not cat_file.exists():
            continue
        with open(cat_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cases.append(EvaluationCase.from_dict(json.loads(line)))
    return cases


def main():
    parser = argparse.ArgumentParser(description="LegalLens Phase 8 Security & Red-Teaming CLI")
    parser.add_argument("--all", action="store_true", help="Run all security tests")
    parser.add_argument("--prompt-injection", action="store_true", help="Test prompt injection")
    parser.add_argument("--jailbreak", action="store_true", help="Test jailbreaks")
    parser.add_argument("--secrets", action="store_true", help="Test canary secret leakage")
    parser.add_argument("--pii", action="store_true", help="Test PII containment")
    parser.add_argument("--tenant-isolation", action="store_true", help="Test multi-tenant isolation")
    parser.add_argument("--file-security", action="store_true", help="Test malformed and oversized payloads")
    parser.add_argument("--provenance", action="store_true", help="Test citation and hash tampering")
    parser.add_argument("--data-dir", type=str, default="legal-data/evaluation", help="Dataset directory")
    parser.add_argument("--output-dir", type=str, default="evaluation-results", help="Output directory")

    args = parser.parse_args()

    run_all = args.all or not (
        args.prompt_injection
        or args.jailbreak
        or args.secrets
        or args.pii
        or args.tenant-isolation
        or args.file-security
        or args.provenance
    )

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    reporter = EvaluationReporter(output_dir=output_dir)
    evaluator = SafetyEvaluator()

    target_cats: List[str] = []
    if run_all or args.prompt_injection:
        target_cats.append("prompt_injection")
    if run_all or args.jailbreak:
        target_cats.append("jailbreak")
    if run_all or args.secrets:
        target_cats.append("secret_leakage")
    if run_all or args.pii:
        target_cats.append("pii_leakage")
    if run_all or args.tenant-isolation:
        target_cats.append("cross_tenant")
    if run_all or args.file-security:
        target_cats.append("malformed_inputs")

    print("=" * 70)
    print("  LegalLens Phase 8 — Dedicated Security Testing & Red-Teaming")
    print(f"  Target Attack Categories: {', '.join(target_cats)}")
    print("=" * 70)

    cases = load_security_cases(data_dir, target_cats)
    print(f"\nLoaded {len(cases)} adversarial test attack vectors.")

    if not cases:
        print("No security cases found! Run pipeline/evaluation/dataset_generator.py first.")
        sys.exit(1)

    assessment = evaluator.evaluate_batch(cases)
    j_path, md_path = reporter.generate_security_reports(assessment)

    sev = assessment.get("severity_breakdown", {})
    print(f"\nResults:")
    print(f"  Total Attacks Executed: {assessment['total_tests']}")
    print(f"  Attacks Neutralized   : {assessment['passed']}")
    print(f"  Breaches / Failures   : {assessment['failed']}")
    print(f"  Vulnerabilities Found : {assessment['findings_count']}")
    print(f"    - Critical: {sev.get('critical', 0)}")
    print(f"    - High    : {sev.get('high', 0)}")
    print(f"    - Medium  : {sev.get('medium', 0)}")
    print(f"    - Low     : {sev.get('low', 0)}")

    if assessment["findings"]:
        print("\nFindings Detail:")
        for f in assessment["findings"]:
            print(f"  [{f['severity']}] {f['title']}: {f['description']}")
    else:
        print("\n[+] All attacks were neutralized by safety guardrails and boundary defenses.")

    print(f"\nReports saved to: {md_path.resolve()}")
    print("=" * 70)

    # Return non-zero if critical or high vulnerabilities found
    if sev.get("critical", 0) > 0 or sev.get("high", 0) > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
