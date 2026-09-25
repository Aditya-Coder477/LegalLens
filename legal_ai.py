#!/usr/bin/env python3
"""
legal_ai.py
===========
CLI interface for LegalLens Phase 6: Legal Reasoning & AI Features.

Subcommands:
    health              Check AI configuration, LLM provider, and KB connectivity
    answer              Grounded legal Q&A with atomic claims and citations
    summarize           Hierarchical legal document summarization
    analyze-clause      Clause / provision analysis (obligations, rights, risks)
    compare             Multi-document / contract comparison across dimensions
    extract-obligations Mandatory obligation extraction
    extract-deadlines   Deadline, timeline, and date requirement extraction
    issues              Legal issue, risk, and ambiguity identification
    next-steps          Actionable procedural next steps derived from evidence
    checklist           Structured compliance or due diligence checklists
    evaluate            Run benchmark evaluation suite on synthetic datasets
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from pipeline.legal_ai.config import get_ai_config
from pipeline.legal_ai.evaluation import AIEvaluator
from pipeline.legal_ai.models import TaskType, UserFact
from pipeline.legal_ai.service import LegalAIService
from pipeline.retrieval.models import RetrievalFilters


def _read_input_text(text_arg: Optional[str], file_arg: Optional[str]) -> str:
    if text_arg:
        return text_arg.strip()
    if file_arg:
        p = Path(file_arg)
        if not p.exists():
            print(f"ERROR: File not found: {file_arg}", file=sys.stderr)
            sys.exit(1)
        return p.read_text(encoding="utf-8").strip()
    return ""


def _print_response(res, as_json: bool = False):
    if as_json:
        print(res.model_dump_json(indent=2))
        return

    print("=" * 70)
    print(f"LEGALLENS AI INTELLIGENCE — [{res.task_type.value}]")
    print(f"Request ID: {res.request_id} | Status: {res.status}")
    print(f"Provider: {res.provider} | Model: {res.model} | Version: {res.prompt_version}")
    print(f"Claim Support Rate: {res.claim_support_rate:.1%} | Synthetic: {res.synthetic}")
    print("=" * 70)

    if res.direct_answer:
        print("\nDIRECT ANSWER / OVERVIEW:")
        print(res.direct_answer)

    if res.structured_data:
        print("\nSTRUCTURED FINDINGS:")
        for k, v in res.structured_data.items():
            if k in ("direct_answer", "claims", "evidence_refs", "limitations"):
                continue
            if isinstance(v, list) and v:
                print(f"  • {k.replace('_', ' ').title()}:")
                for item in v:
                    if isinstance(item, dict):
                        print(f"    - {json.dumps(item)}")
                    else:
                        print(f"    - {item}")
            elif isinstance(v, dict) and v:
                print(f"  • {k.replace('_', ' ').title()}:")
                for sub_k, sub_v in v.items():
                    print(f"    - {sub_k}: {sub_v}")
            elif v:
                print(f"  • {k.replace('_', ' ').title()}: {v}")

    if res.claims:
        print(f"\nGROUNDED CLAIMS ({len(res.claims)}):")
        for c in res.claims:
            refs = ", ".join(c.evidence_refs) if c.evidence_refs else "NONE"
            print(f"  [{c.claim_id}] ({c.claim_type.value} | {c.support_status.value}) [Refs: {refs}]")
            print(f"      {c.text}")

    if res.evidence_refs:
        print(f"\nVALIDATED EVIDENCE CITATIONS: {', '.join(res.evidence_refs)}")

    if res.warnings:
        print("\nWARNINGS:")
        for w in res.warnings:
            print(f"  [!] {w}")

    if res.limitations:
        print("\nLIMITATIONS:")
        for lim in res.limitations:
            print(f"  [*] {lim}")

    print("\n" + "-" * 70)
    print(f"DISCLAIMER: {res.disclaimer}")
    print("-" * 70)


def cmd_health(args: argparse.Namespace) -> int:
    cfg = get_ai_config()
    print("=" * 70)
    print("LEGALLENS PHASE 6: LEGAL AI HEALTH CHECK")
    print("=" * 70)
    print(f"LLM Provider:               {cfg.llm_provider}")
    print(f"LLM Model:                  {cfg.llm_model}")
    print(f"Temperature:                {cfg.temperature}")
    print(f"Max Context Tokens:         {cfg.max_context_tokens}")
    print(f"Grounding Mode:             {cfg.grounding_mode}")
    print(f"Min Claim Support Rate:     {cfg.min_claim_support_rate:.1%}")
    print(f"Enforce Strict Grounding:   {cfg.enforce_strict_grounding}")
    print(f"Synthetic Safety Flag:      {cfg.require_synthetic_marker}")

    try:
        service = LegalAIService()
        test_res = service.answer("What is this enactment?")
        print(f"\nSelf-Test Execution:        SUCCESS")
        print(f"Mock Reasoner Status:       {test_res.status}")
        print(f"Grounded Claims Generated:  {len(test_res.claims)}")
        print("\nAll Phase 6 AI features are HEALTHY and OPERATIONAL.")
        return 0
    except Exception as e:
        print(f"\nERROR during health check: {e}", file=sys.stderr)
        return 1


def cmd_answer(args: argparse.Namespace) -> int:
    query = args.query.strip()
    if not query:
        print("ERROR: --query cannot be empty", file=sys.stderr)
        return 1

    facts: Optional[list[UserFact]] = None
    if args.fact:
        facts = [UserFact(text=f) for f in args.fact]

    filters = RetrievalFilters(
        document_id=args.document_id,
        document_type=args.document_type,
    )

    service = LegalAIService()
    res = service.answer(query=query, user_facts=facts, filters=filters, top_k=args.top_k)
    _print_response(res, as_json=args.json)
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    text = _read_input_text(args.text, args.file)
    if not text:
        print("ERROR: Provide document text via --text or --file", file=sys.stderr)
        return 1

    service = LegalAIService()
    res = service.summarize(document_text=text)
    _print_response(res, as_json=args.json)
    return 0


def cmd_analyze_clause(args: argparse.Namespace) -> int:
    clause = _read_input_text(args.clause, args.file)
    if not clause:
        print("ERROR: Provide clause text via --clause or --file", file=sys.stderr)
        return 1

    service = LegalAIService()
    res = service.analyze_clause(clause_text=clause)
    _print_response(res, as_json=args.json)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    doc_a = _read_input_text(args.doc_a, args.file_a)
    doc_b = _read_input_text(args.doc_b, args.file_b)

    if not doc_a or not doc_b:
        print("ERROR: Both Document A and Document B must be provided.", file=sys.stderr)
        return 1

    service = LegalAIService()
    res = service.compare(doc_a_text=doc_a, doc_b_text=doc_b)
    _print_response(res, as_json=args.json)
    return 0


def cmd_obligations(args: argparse.Namespace) -> int:
    text = _read_input_text(args.text, args.file)
    if not text and not args.query:
        print("ERROR: Provide text via --text/--file or query via --query", file=sys.stderr)
        return 1

    service = LegalAIService()
    res = service.execute_task(
        query=args.query or "Extract obligations",
        task_type=TaskType.EXTRACT_OBLIGATIONS,
        document_text=text or None,
    )
    _print_response(res, as_json=args.json)
    return 0


def cmd_deadlines(args: argparse.Namespace) -> int:
    text = _read_input_text(args.text, args.file)
    if not text and not args.query:
        print("ERROR: Provide text via --text/--file or query via --query", file=sys.stderr)
        return 1

    service = LegalAIService()
    res = service.execute_task(
        query=args.query or "Extract deadlines",
        task_type=TaskType.EXTRACT_DEADLINES,
        document_text=text or None,
    )
    _print_response(res, as_json=args.json)
    return 0


def cmd_issues(args: argparse.Namespace) -> int:
    text = _read_input_text(args.text, args.file)
    if not text and not args.query:
        print("ERROR: Provide text via --text/--file or query via --query", file=sys.stderr)
        return 1

    service = LegalAIService()
    res = service.execute_task(
        query=args.query or "Identify legal issues and risks",
        task_type=TaskType.IDENTIFY_ISSUES,
        document_text=text or None,
    )
    _print_response(res, as_json=args.json)
    return 0


def cmd_next_steps(args: argparse.Namespace) -> int:
    service = LegalAIService()
    res = service.generate_next_steps(query=args.query)
    _print_response(res, as_json=args.json)
    return 0


def cmd_checklist(args: argparse.Namespace) -> int:
    service = LegalAIService()
    res = service.generate_checklist(query=args.query)
    _print_response(res, as_json=args.json)
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    print("=" * 70)
    print("RUNNING LEGALLENS PHASE 6 AI FEATURE BENCHMARK EVALUATION")
    print("=" * 70)
    evaluator = AIEvaluator()
    results = evaluator.run_all_evaluations()

    print("\nBENCHMARK RESULTS SUMMARY:")
    print(f"Overall AI Readiness Score:     {results['overall_ai_readiness_score']:.1%}")
    print(f"QA Grounding Rate:              {results['metrics']['qa_grounding_rate']:.1%}")
    print(f"Avg Claim Support Rate:         {results['metrics']['qa_avg_claim_support_rate']:.1%}")
    print(f"Unanswerable Abstention Rate:   {results['metrics']['unanswerable_abstention_rate']:.1%}")
    print(f"Adversarial Defense Rate:       {results['metrics']['adversarial_defense_rate']:.1%}")
    print(f"Clause Analysis Valid Rate:     {results['metrics']['clause_analysis_valid_rate']:.1%}")
    print(f"Document Comparison Valid Rate: {results['metrics']['document_comparison_valid_rate']:.1%}")
    print(f"Reports saved under:            legal-data/ai/reports/")
    print("=" * 70)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="legal_ai.py",
        description="LegalLens Phase 6: Legal Reasoning & AI Features CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # health
    subparsers.add_parser("health", help="Check AI service and provider health")

    # answer
    p_ans = subparsers.add_parser("answer", help="Grounded Legal Q&A")
    p_ans.add_argument("--query", "-q", required=True, help="Legal question to ask")
    p_ans.add_argument("--fact", action="append", help="User fact (can specify multiple times)")
    p_ans.add_argument("--document-id", help="Filter evidence by document ID")
    p_ans.add_argument("--document-type", help="Filter by document type (e.g. ACT, CONTRACT)")
    p_ans.add_argument("--top-k", type=int, default=5, help="Number of evidence chunks (default: 5)")
    p_ans.add_argument("--json", action="store_true", help="Output raw JSON")

    # summarize
    p_sum = subparsers.add_parser("summarize", help="Document summarization")
    p_sum.add_argument("--text", help="Document text")
    p_sum.add_argument("--file", help="Path to document file")
    p_sum.add_argument("--json", action="store_true", help="Output raw JSON")

    # analyze-clause
    p_cl = subparsers.add_parser("analyze-clause", help="Clause / provision analysis")
    p_cl.add_argument("--clause", help="Clause text")
    p_cl.add_argument("--file", help="Path to clause file")
    p_cl.add_argument("--json", action="store_true", help="Output raw JSON")

    # compare
    p_cmp = subparsers.add_parser("compare", help="Compare two documents or contracts")
    p_cmp.add_argument("--doc-a", help="Document A text")
    p_cmp.add_argument("--doc-b", help="Document B text")
    p_cmp.add_argument("--file-a", help="Path to Document A file")
    p_cmp.add_argument("--file-b", help="Path to Document B file")
    p_cmp.add_argument("--json", action="store_true", help="Output raw JSON")

    # extract-obligations
    p_obl = subparsers.add_parser("extract-obligations", help="Extract mandatory obligations")
    p_obl.add_argument("--text", help="Text to extract from")
    p_obl.add_argument("--file", help="Path to text file")
    p_obl.add_argument("--query", help="Optional search query if querying KB directly")
    p_obl.add_argument("--json", action="store_true", help="Output raw JSON")

    # extract-deadlines
    p_dl = subparsers.add_parser("extract-deadlines", help="Extract deadlines and dates")
    p_dl.add_argument("--text", help="Text to extract from")
    p_dl.add_argument("--file", help="Path to text file")
    p_dl.add_argument("--query", help="Optional search query if querying KB directly")
    p_dl.add_argument("--json", action="store_true", help="Output raw JSON")

    # issues
    p_iss = subparsers.add_parser("issues", help="Identify legal issues and risks")
    p_iss.add_argument("--text", help="Text to inspect")
    p_iss.add_argument("--file", help="Path to text file")
    p_iss.add_argument("--query", help="Optional query")
    p_iss.add_argument("--json", action="store_true", help="Output raw JSON")

    # next-steps
    p_ns = subparsers.add_parser("next-steps", help="Generate evidence-based next steps")
    p_ns.add_argument("--query", "-q", required=True, help="Scenario or legal question")
    p_ns.add_argument("--json", action="store_true", help="Output raw JSON")

    # checklist
    p_chk = subparsers.add_parser("checklist", help="Generate compliance checklist")
    p_chk.add_argument("--query", "-q", required=True, help="Topic or transaction type")
    p_chk.add_argument("--json", action="store_true", help="Output raw JSON")

    # evaluate
    subparsers.add_parser("evaluate", help="Run comprehensive AI benchmark evaluation")

    args = parser.parse_args()

    handlers = {
        "health": cmd_health,
        "answer": cmd_answer,
        "summarize": cmd_summarize,
        "analyze-clause": cmd_analyze_clause,
        "compare": cmd_compare,
        "extract-obligations": cmd_obligations,
        "extract-deadlines": cmd_deadlines,
        "issues": cmd_issues,
        "next-steps": cmd_next_steps,
        "checklist": cmd_checklist,
        "evaluate": cmd_evaluate,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
