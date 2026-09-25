"""
pipeline/evaluation/reporter.py
===============================
Report generation module for LegalLens Phase 8.
Generates all machine-readable (JSON, CSV) and human-readable (Markdown) reports
and saves them into `evaluation-results/`.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("legallens.evaluation.reporter")


class EvaluationReporter:
    """
    Renders and writes all benchmark, security, and quality gate reports.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("evaluation-results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, filename: str, data: Any) -> Path:
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return filepath

    def write_text(self, filename: str, content: str) -> Path:
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def generate_traceability_matrix(self, all_cases: List[Dict[str, Any]]) -> Path:
        """
        Generate traceability_matrix.csv mapping cases to requirements, test type, and results.
        """
        filepath = self.output_dir / "traceability_matrix.csv"
        fieldnames = ["case_id", "category", "evaluation_layer", "query", "expected_documents", "expected_sections", "synthetic"]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in all_cases:
                writer.writerow({
                    "case_id": c.get("case_id"),
                    "category": c.get("category"),
                    "evaluation_layer": c.get("evaluation_layer"),
                    "query": c.get("query", "")[:100],
                    "expected_documents": "|".join(c.get("expected_documents", [])),
                    "expected_sections": "|".join(c.get("expected_sections", [])),
                    "synthetic": c.get("synthetic", True),
                })
        return filepath

    def generate_dashboard_json(
        self,
        retrieval_data: Dict[str, Any],
        qa_data: Dict[str, Any],
        grounding_data: Dict[str, Any],
        citation_data: Dict[str, Any],
        security_data: Dict[str, Any],
        performance_data: Dict[str, Any],
        quality_gate_data: Dict[str, Any],
    ) -> Path:
        """
        Generate aggregate dashboard.json for UI / CI integrations.
        """
        dashboard = {
            "title": "LegalLens Phase 8 Evaluation & Safety Dashboard",
            "timestamp": datetime.utcnow().isoformat(),
            "synthetic_disclaimer": "ALL EVALUATION DATA USES SYNTHETIC INDIAN LEGAL DATA (source_authority=SYNTHETIC)",
            "quality_gate": {
                "status": quality_gate_data.get("status"),
                "passed": quality_gate_data.get("passed"),
                "blockers": quality_gate_data.get("blockers", []),
                "warnings": quality_gate_data.get("warnings", []),
            },
            "summary_metrics": {
                "retrieval_hybrid_recall_at_10": retrieval_data.get("metrics_by_strategy", {}).get("hybrid", {}).get("recall@10"),
                "retrieval_hybrid_mrr": retrieval_data.get("metrics_by_strategy", {}).get("hybrid", {}).get("mrr"),
                "retrieval_hybrid_ndcg_at_10": retrieval_data.get("metrics_by_strategy", {}).get("hybrid", {}).get("ndcg@10"),
                "qa_pass_rate": qa_data.get("pass_rate"),
                "grounding_unsupported_rate": grounding_data.get("metrics", {}).get("unsupported_claim_rate"),
                "citation_validity_rate": citation_data.get("metrics", {}).get("overall_citation_validity_rate"),
                "security_critical_findings": security_data.get("severity_breakdown", {}).get("critical", 0),
                "security_high_findings": security_data.get("severity_breakdown", {}).get("high", 0),
                "p95_end_to_end_latency_ms": performance_data.get("latency_stats", {}).get("end_to_end", {}).get("p95"),
            },
            "retrieval_strategies": retrieval_data.get("metrics_by_strategy", {}),
            "failure_taxonomy": retrieval_data.get("failure_taxonomy", {}),
            "security_breakdown": security_data.get("severity_breakdown", {}),
        }
        return self.write_json("dashboard.json", dashboard)

    def generate_retrieval_reports(self, retrieval_data: Dict[str, Any]) -> Tuple[Path, Path]:
        j_path = self.write_json("retrieval_benchmark.json", retrieval_data)

        # Markdown report
        metrics_by_strat = retrieval_data.get("metrics_by_strategy", {})
        md = ["# LegalLens IR Retrieval Benchmark Report", "", "## Strategy Comparison Table", ""]
        md.append("| Strategy | Recall@1 | Recall@5 | Recall@10 | Precision@10 | MRR | NDCG@10 | Avg Latency (ms) |")
        md.append("|---|---|---|---|---|---|---|---|")
        for strat, m in metrics_by_strat.items():
            md.append(f"| **{strat}** | {m.get('recall@1', 0):.3f} | {m.get('recall@5', 0):.3f} | {m.get('recall@10', 0):.3f} | {m.get('precision@10', 0):.3f} | {m.get('mrr', 0):.3f} | {m.get('ndcg@10', 0):.3f} | {m.get('avg_latency_ms', 0):.1f} |")

        md.extend(["", "## Failure Taxonomy", ""])
        for cause, count in retrieval_data.get("failure_taxonomy", {}).items():
            md.append(f"- **{cause}**: {count} cases")

        md_path = self.write_text("retrieval_benchmark.md", "\n".join(md))
        return j_path, md_path

    def generate_qa_reports(self, qa_data: Dict[str, Any]) -> Tuple[Path, Path]:
        j_path = self.write_json("qa_evaluation.json", qa_data)
        md = [
            "# Legal AI Reasoning & QA Evaluation Report",
            "",
            f"- **Total Cases**: {qa_data.get('total_cases')}",
            f"- **Passed**: {qa_data.get('passed')}",
            f"- **Pass Rate**: {qa_data.get('pass_rate') * 100:.1f}%",
            f"- **Avg Latency**: {qa_data.get('avg_latency_ms')} ms",
        ]
        md_path = self.write_text("qa_evaluation.md", "\n".join(md))
        return j_path, md_path

    def generate_grounding_reports(self, grounding_data: Dict[str, Any]) -> Tuple[Path, Path]:
        j_path = self.write_json("grounding_benchmark.json", grounding_data)
        m = grounding_data.get("metrics", {})
        md = [
            "# Legal Grounding & NLI Benchmark Report",
            "",
            f"- **Total Cases**: {grounding_data.get('total_cases')}",
            f"- **Claim Support Rate**: {m.get('claim_support_rate', 0) * 100:.1f}%",
            f"- **Unsupported Claim Rate**: {m.get('unsupported_claim_rate', 0) * 100:.1f}%",
            f"- **Contradiction Rate**: {m.get('contradiction_rate', 0) * 100:.1f}%",
            f"- **Partial Support Rate**: {m.get('partial_support_rate', 0) * 100:.1f}%",
        ]
        md_path = self.write_text("grounding_benchmark.md", "\n".join(md))
        return j_path, md_path

    def generate_citation_reports(self, citation_data: Dict[str, Any]) -> Tuple[Path, Path]:
        j_path = self.write_json("citation_benchmark.json", citation_data)
        m = citation_data.get("metrics", {})
        md = [
            "# Citation & Provenance Integrity Benchmark Report",
            "",
            f"- **Citations Evaluated**: {m.get('total_citations_evaluated')}",
            f"- **Overall Validity Rate**: {m.get('overall_citation_validity_rate', 0) * 100:.1f}%",
            f"- **SHA-256 Match Rate**: {m.get('overall_sha256_match_rate', 0) * 100:.1f}%",
        ]
        md_path = self.write_text("citation_benchmark.md", "\n".join(md))
        return j_path, md_path

    def generate_security_reports(self, security_data: Dict[str, Any]) -> Tuple[Path, Path]:
        j_path = self.write_json("security_assessment.json", security_data)
        sev = security_data.get("severity_breakdown", {})
        md = [
            "# Security & Adversarial Red-Teaming Report",
            "",
            f"- **Total Security Tests**: {security_data.get('total_tests')}",
            f"- **Tests Passed**: {security_data.get('passed')}",
            f"- **Critical Vulnerabilities**: {sev.get('critical', 0)}",
            f"- **High Vulnerabilities**: {sev.get('high', 0)}",
            f"- **Medium Findings**: {sev.get('medium', 0)}",
            f"- **Low Findings**: {sev.get('low', 0)}",
            "",
            "## Findings Log",
        ]
        findings = security_data.get("findings", [])
        if not findings:
            md.append("No active vulnerabilities discovered. All attacks successfully neutralized.")
        else:
            for f in findings:
                md.append(f"### [{f.get('severity')}] {f.get('title')}")
                md.append(f"- **ID**: {f.get('finding_id')}")
                md.append(f"- **Description**: {f.get('description')}")
                md.append(f"- **Remediation**: {f.get('remediation')}")
                md.append("")
        md_path = self.write_text("security_assessment.md", "\n".join(md))
        return j_path, md_path

    def generate_performance_reports(self, performance_data: Dict[str, Any]) -> Tuple[Path, Path]:
        j_path = self.write_json("performance_benchmark.json", performance_data)
        lat = performance_data.get("latency_stats", {})
        md = [
            "# System Performance & Latency Benchmark",
            "",
            "| Component | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Min (ms) | Max (ms) |",
            "|---|---|---|---|---|---|---|",
        ]
        for comp, s in lat.items():
            md.append(f"| **{comp}** | {s.get('mean', 0):.1f} | {s.get('p50', 0):.1f} | {s.get('p95', 0):.1f} | {s.get('p99', 0):.1f} | {s.get('min', 0):.1f} | {s.get('max', 0):.1f} |")

        md_path = self.write_text("performance_benchmark.md", "\n".join(md))
        return j_path, md_path

    def generate_quality_gate_reports(self, quality_gate_data: Dict[str, Any]) -> Tuple[Path, Path]:
        j_path = self.write_json("quality_gate_report.json", quality_gate_data)
        md = [
            f"# Quality Gate Assessment: {quality_gate_data.get('status')}",
            "",
            f"**Overall Passed**: `{quality_gate_data.get('passed')}`",
            "",
            "## Dimension Breakdown",
            "",
            "| Dimension | Metric | Actual | Target Threshold | Status |",
            "|---|---|---|---|---|",
        ]
        for dim in quality_gate_data.get("dimensions", []):
            passed_emoji = "✅ PASS" if dim.get("passed") else "❌ FAIL"
            md.append(f"| {dim.get('name')} | {dim.get('metric_name')} | {dim.get('actual_value')} | {dim.get('threshold')} | {passed_emoji} |")

        if quality_gate_data.get("blockers"):
            md.extend(["", "### Critical Blockers:"])
            for b in quality_gate_data["blockers"]:
                md.append(f"- 🛑 {b}")

        if quality_gate_data.get("warnings"):
            md.extend(["", "### Warnings:"])
            for w in quality_gate_data["warnings"]:
                md.append(f"- ⚠️ {w}")

        md_path = self.write_text("quality_gate_report.md", "\n".join(md))
        return j_path, md_path
