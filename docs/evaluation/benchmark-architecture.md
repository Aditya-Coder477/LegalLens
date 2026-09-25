# LegalLens Benchmark Architecture

## 1. Overview
The LegalLens Phase 8 evaluation framework provides a comprehensive, multi-layer evaluation, benchmarking, adversarial testing, and quality-gate system designed specifically for Indian legal information retrieval and reasoning.

The system is deterministic and reproducible using seed `20260925`.

## 2. Multi-Layer Evaluation Hierarchy

```
Layer 7: Safety & Adversarial Security
   ▲
Layer 6: Citation & Provenance Integrity (SHA-256)
   ▲
Layer 5: Claim Grounding & Faithfulness (NLI)
   ▲
Layer 4: AI Legal Reasoning & Answer Quality
   ▲
Layer 3: Evidence Selection & Packaging
   ▲
Layer 2: Information Retrieval (Lexical, Semantic, Hybrid, Rerank, Expansion)
   ▲
Layer 1: Corpus Quality & Ingestion Integrity
```

## 3. Evaluation Datasets
Datasets are stored under `legal-data/evaluation/`:
- `retrieval/`: IR benchmarking queries with graded relevance (0..3).
- `qa/`: Grounded questions, unanswerable queries (abstention check), statutory contradictions, and version-aware queries.
- `grounding/`: Claim-level entailment benchmarks.
- `citations/`: Citation verification benchmarks resolving against Knowledge Base chunks and SHA-256 hashes.
- `security/`: Red-teaming attack vectors covering prompt injection, jailbreaks, canaries, PII, and multi-tenant isolation.
- `manifests/`: Traceability matrix and regression baselines.

## 4. Determinism & Offline Execution
All benchmarks can run in `mock` or `offline` mode without external network dependencies, ensuring zero CI flakiness and high test velocity.
