"""
evaluate.py
===========
Master Evaluation & Benchmarking CLI for LegalLens Phase 8.
Runs comprehensive multi-layer evaluation across:
- Information Retrieval (Lexical, Semantic, Hybrid, Rerank, Expansion)
- Legal AI Reasoning (Grounded QA, Abstention, Contradictions, Versioning)
- Grounding & NLI Faithfulness
- Citation & Provenance Integrity
- Adversarial Security & Red-Teaming
- Performance & Latency Benchmarks
- Automated Quality Gate Assessment

Usage:
  python evaluate.py --all
  python evaluate.py --retrieval
  python evaluate.py --qa
  python evaluate.py --grounding
  python evaluate.py --citations
  python evaluate.py --security
  python evaluate.py --performance
  python evaluate.py --category <category_name>
  python evaluate.py --case <case_id>
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from pipeline.evaluation.citation_evaluator import CitationEvaluator
from pipeline.evaluation.config import EvaluationConfig, get_evaluation_config
from pipeline.evaluation.grounding_evaluator import GroundingEvaluator
from pipeline.evaluation.models import EvaluationCase
from pipeline.evaluation.performance_evaluator import PerformanceEvaluator
from pipeline.evaluation.qa_evaluator import QAEvaluator
from pipeline.evaluation.quality_gate import QualityGate
from pipeline.evaluation.reporter import EvaluationReporter
from pipeline.evaluation.retrieval_evaluator import RetrievalEvaluator
from pipeline.evaluation.safety_evaluator import SafetyEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("legallens.evaluate")


def load_dataset_cases(data_dir: Path, category_filter: str = None, case_filter: str = None) -> List[EvaluationCase]:
    """
    Load evaluation cases from all JSONL files in legal-data/evaluation/.
    """
    cases: List[EvaluationCase] = []
    pattern = str(data_dir / "**" / "*.jsonl")
    for file_path in glob.glob(pattern, recursive=True):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                case = EvaluationCase.from_dict(data)
                if case_filter and case.case_id != case_filter:
                    continue
                if category_filter and case.category != category_filter:
                    continue
                cases.append(case)
    return cases


def main():
    parser = argparse.ArgumentParser(description="LegalLens Phase 8 Evaluation Runner")
    parser.add_argument("--all", action="store_true", help="Run full evaluation across all dimensions")
    parser.add_argument("--retrieval", action="store_true", help="Run retrieval benchmark")
    parser.add_argument("--qa", action="store_true", help="Run legal reasoning / QA evaluation")
    parser.add_argument("--grounding", action="store_true", help="Run grounding benchmark")
    parser.add_argument("--citations", action="store_true", help="Run citation benchmark")
    parser.add_argument("--security", action="store_true", help="Run security assessment")
    parser.add_argument("--performance", action="store_true", help="Run performance & latency benchmark")
    parser.add_argument("--gate", action="store_true", help="Run quality gate check only")
    parser.add_argument("--category", type=str, default=None, help="Filter by evaluation category")
    parser.add_argument("--case", type=str, default=None, help="Filter by single case ID")
    parser.add_argument("--data-dir", type=str, default="legal-data/evaluation", help="Dataset directory")
    parser.add_argument("--output-dir", type=str, default="evaluation-results", help="Output directory for reports")
    parser.add_argument("--seed", type=int, default=20260925, help="Deterministic seed")

    args = parser.parse_args()

    # Default to --all if no specific layer selected
    run_all = args.all or not (
        args.retrieval
        or args.qa
        or args.grounding
        or args.citations
        or args.security
        or args.performance
        or args.gate
        or args.category
        or args.case
    )

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    reporter = EvaluationReporter(output_dir=output_dir)
    config = get_evaluation_config()
    config.random_seed = args.seed

    print("=" * 70)
    print("  LegalLens Phase 8 — Evaluation & Benchmarking System")
    print(f"  Random Seed: {config.random_seed} | Deterministic Run")
    print("  Corpus: SYNTHETIC Indian Legal Corpus (source_authority=SYNTHETIC)")
    print("=" * 70)

    all_cases = load_dataset_cases(data_dir, category_filter=args.category, case_filter=args.case)
    print(f"\nLoaded {len(all_cases)} total evaluation cases from {data_dir}\n")

    if not all_cases:
        print("No evaluation cases found! Run pipeline/evaluation/dataset_generator.py first.")
        sys.exit(1)

    # Save traceability matrix
    reporter.generate_traceability_matrix([c.to_dict() for c in all_cases])

    retrieval_data = {}
    qa_data = {}
    grounding_data = {}
    citation_data = {}
    security_data = {}
    performance_data = {}
    quality_gate_data = {}

    # 1. Retrieval Benchmark
    if run_all or args.retrieval:
        ret_cases = [c for c in all_cases if c.category in ("retrieval", "comparison", "clauses")][:25]
        if not ret_cases:
            ret_cases = all_cases[:25]
        print(f"[*] Running Retrieval IR Benchmark on {len(ret_cases)} cases...")
        ret_eval = RetrievalEvaluator(config=config)
        retrieval_data = ret_eval.evaluate_benchmark(ret_cases)
        reporter.generate_retrieval_reports(retrieval_data)
        hybrid_rec10 = retrieval_data["metrics_by_strategy"].get("hybrid", {}).get("recall@10", 0.0)
        hybrid_mrr = retrieval_data["metrics_by_strategy"].get("hybrid", {}).get("mrr", 0.0)
        hybrid_ndcg = retrieval_data["metrics_by_strategy"].get("hybrid", {}).get("ndcg@10", 0.0)
        print(f"    -> Hybrid Retrieval: Recall@10 = {hybrid_rec10:.3f}, MRR = {hybrid_mrr:.3f}, NDCG@10 = {hybrid_ndcg:.3f}")

    # 2. QA & Legal Reasoning Evaluation
    if run_all or args.qa:
        qa_cases = [c for c in all_cases if c.category in ("qa", "summarization")][:20]
        if not qa_cases:
            qa_cases = all_cases[:20]
        print(f"[*] Running Legal AI Reasoning & Abstention Evaluation on {len(qa_cases)} cases...")
        qa_eval = QAEvaluator(config=config)
        qa_data = qa_eval.evaluate_batch(qa_cases)
        reporter.generate_qa_reports(qa_data)
        print(f"    -> QA Pass Rate: {qa_data['pass_rate'] * 100:.1f}% ({qa_data['passed']}/{qa_data['total_cases']})")

    # 3. Grounding & Faithfulness Benchmark
    if run_all or args.grounding:
        ground_cases = [c for c in all_cases if c.category in ("grounding", "qa")][:15]
        if not ground_cases:
            ground_cases = all_cases[:15]
        print(f"[*] Running Grounding & NLI Verification Benchmark on {len(ground_cases)} cases...")
        g_eval = GroundingEvaluator(config=config)
        grounding_data = g_eval.evaluate_batch(ground_cases)
        reporter.generate_grounding_reports(grounding_data)
        unsupp = grounding_data.get("metrics", {}).get("unsupported_claim_rate", 0.0)
        print(f"    -> Unsupported Claim Rate: {unsupp * 100:.1f}% (target <= {config.max_unsupported_claim_rate * 100:.1f}%)")

    # 4. Citation & Provenance Benchmark
    if run_all or args.citations:
        cit_cases = [c for c in all_cases if c.category in ("citations", "retrieval")][:15]
        if not cit_cases:
            cit_cases = all_cases[:15]
        print(f"[*] Running Citation & SHA-256 Provenance Verification on {len(cit_cases)} cases...")
        c_eval = CitationEvaluator(config=config)
        citation_data = c_eval.evaluate_batch(cit_cases)
        reporter.generate_citation_reports(citation_data)
        validity = citation_data.get("metrics", {}).get("overall_citation_validity_rate", 0.0)
        sha_rate = citation_data.get("metrics", {}).get("overall_sha256_match_rate", 0.0)
        print(f"    -> Citation Validity: {validity * 100:.1f}%, SHA-256 Match: {sha_rate * 100:.1f}%")

    # 5. Security & Red-Teaming Assessment
    if run_all or args.security:
        sec_cases = [c for c in all_cases if c.category == "security"][:15]
        if not sec_cases:
            sec_cases = all_cases[:15]
        print(f"[*] Running Adversarial Red-Teaming & Safety Assessment on {len(sec_cases)} attack tests...")
        s_eval = SafetyEvaluator(config=config)
        security_data = s_eval.evaluate_batch(sec_cases)
        reporter.generate_security_reports(security_data)
        sev = security_data.get("severity_breakdown", {})
        print(f"    -> Security Defense: {security_data['passed']}/{security_data['total_tests']} neutralized")
        print(f"    -> Vulnerabilities: Critical={sev.get('critical', 0)}, High={sev.get('high', 0)}, Medium={sev.get('medium', 0)}")

    # 6. Performance & Latency Benchmark
    if run_all or args.performance:
        perf_cases = all_cases[:5]
        print(f"[*] Running Performance & Latency Profiling across pipeline stages...")
        p_eval = PerformanceEvaluator(config=config)
        performance_data = p_eval.benchmark_pipeline(perf_cases, iterations=1)
        reporter.generate_performance_reports(performance_data)
        p95_e2e = performance_data.get("latency_stats", {}).get("end_to_end", {}).get("p95", 0.0)
        print(f"    -> P95 End-to-End Latency: {p95_e2e:.1f} ms")

    # 7. Quality Gate Assessment
    if run_all or args.gate:
        print("\n[*] Evaluating Quality Gate Readiness against configured thresholds...")
        qg = QualityGate(config=config)
        prod_ret = retrieval_data.get("metrics_by_strategy", {}).get("hybrid_rerank") or retrieval_data.get("metrics_by_strategy", {}).get("hybrid", {})
        qg_result = qg.evaluate(
            retrieval_metrics=prod_ret,
            grounding_metrics=grounding_data.get("metrics", {}),
            citation_metrics=citation_data.get("metrics", {}),
            security_findings=security_data.get("findings", []),
            performance_stats=performance_data,
        )
        quality_gate_data = qg_result.to_dict()
        reporter.generate_quality_gate_reports(quality_gate_data)
        status_color = "PASS" if qg_result.passed else ("REVIEW" if qg_result.status.value == "REVIEW" else "FAIL")
        print(f"    -> Quality Gate Status: [{status_color}]")
        for dim in qg_result.dimensions:
            dim_status = "PASS" if dim.passed else "FAIL"
            print(f"       - {dim.name:<30}: {dim.actual_value} (Threshold: {dim.threshold}) [{dim_status}]")

    # Final Dashboard Generation
    if run_all:
        reporter.generate_dashboard_json(
            retrieval_data=retrieval_data,
            qa_data=qa_data,
            grounding_data=grounding_data,
            citation_data=citation_data,
            security_data=security_data,
            performance_data=performance_data,
            quality_gate_data=quality_gate_data,
        )
        # Also write summary json
        summary = {
            "timestamp": datetime.utcnow().isoformat() if "datetime" in globals() else None,
            "quality_gate": quality_gate_data.get("status"),
            "reports_generated_in": str(output_dir),
        }
        reporter.write_json("evaluation_summary.json", summary)

    print("\n" + "=" * 70)
    print(f"Evaluation complete. All reports written to: {output_dir.resolve()}/")
    print("=" * 70)


if __name__ == "__main__":
    from datetime import datetime
    main()
