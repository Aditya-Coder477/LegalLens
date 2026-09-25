# Regression Testing Framework

## 1. Overview
The Regression Testing Framework ensures that modifications to retrieval embeddings, query processing, or LLM system prompts do not introduce regressions into core legal workflows.

## 2. Manifest-Driven Baselines
The regression suite is defined by `tests/regression/regression_manifest.json`, specifying:
- **Baseline metrics**: Historical performance bars for Recall@10, MRR, NDCG, and claim support.
- **Golden Queries**: Core legal queries with verified ground truth documents.

## 3. Test Coverage
- `test_regression_retrieval.py`: Retrieval accuracy on golden queries.
- `test_regression_qa.py`: Grounded answers on key statutory questions.
- `test_regression_citations.py`: Citation resolution for verified documents.
- `test_regression_grounding.py`: Entailment validation.
- `test_regression_clauses.py`: Clause extraction schema stability.
- `test_regression_summarization.py`: Statute summarization stability.
- `test_regression_contradictions.py`: Contradiction articulation.
- `test_regression_versioning.py`: Version-aware inquiries.
- `test_regression_obligations.py`: Mandatory obligation extraction.
- `test_regression_benchmarks.py`: Metric bar compliance against manifest.
