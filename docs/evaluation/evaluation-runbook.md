# Phase 8 Evaluation Runbook

## 1. Quick Start Commands

### A. Run Full Multi-Layer Evaluation
```bash
python evaluate.py --all
```
This executes:
1. Information Retrieval Benchmark (5 strategies across 25 queries)
2. Legal AI Reasoning & Abstention Evaluation
3. Claim Grounding & Faithfulness Benchmark
4. Citation & SHA-256 Provenance Benchmark
5. Security Red-Teaming (70 attack vectors)
6. Latency Profiling across pipeline stages
7. Automated Quality Gate Assessment

### B. Run Dedicated Security Red-Teaming
```bash
python security_test.py --all
```

### C. Run Specific Layer Benchmarks
```bash
python evaluate.py --retrieval
python evaluate.py --qa
python evaluate.py --grounding
python evaluate.py --citations
python evaluate.py --security
python evaluate.py --performance
python evaluate.py --gate
```

### D. Run Automated Test Suites
```bash
# Evaluation tests
python -m pytest tests/evaluation/ -v

# Security tests
python -m pytest tests/security/ -v

# Regression tests
python -m pytest tests/regression/ -v
```

## 2. Generated Reports
All results are written to `evaluation-results/`:
- `dashboard.json`: Aggregated dashboard payload for UI / CI integrations.
- `traceability_matrix.csv`: Test case mapping to statutory requirements and results.
- `retrieval_benchmark.json` / `.md`: IR metrics across 5 search strategies.
- `qa_evaluation.json` / `.md`: Grounded QA, unanswerable queries, and contradiction handling.
- `grounding_benchmark.json` / `.md`: Claim support, unsupported, and contradiction rates.
- `citation_benchmark.json` / `.md`: Citation resolution and SHA-256 verification rates.
- `security_assessment.json` / `.md`: Vulnerability findings and remediation recommendations.
- `performance_benchmark.json` / `.md`: Latency distributions and SLA compliance.
- `quality_gate_report.json` / `.md`: PASS / REVIEW / FAIL determination.
