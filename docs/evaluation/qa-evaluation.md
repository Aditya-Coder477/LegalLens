# Legal AI Reasoning & QA Evaluation

## 1. Overview
Evaluating generative AI on legal queries requires verifying factual correctness, grounded reasoning, strict abstention when evidence is absent, and nuanced handling of statutory conflicts.

## 2. Test Dimensions

### A. Grounded Q&A (`grounded_qa`)
- Evaluates whether the generated response accurately answers legal queries based solely on retrieved evidence.
- Verifies that statutory provisions, penalties, and definitions are cited.

### B. Unanswerable Queries & Abstention (`unanswerable_qa`)
- Tests queries that fall outside the synthetic corpus (e.g. extraterrestrial maritime law, non-existent acts).
- Verifies that the model explicitly abstains or indicates lack of authoritative evidence rather than hallucinating plausible-sounding statutes.

### C. Contradictory Provisions (`contradiction_qa`)
- Evaluates scenarios where an Act and subsequent Rules conflict or where general provisions are modified by specific provisos.
- Verifies that the model detects the hierarchy (e.g. Act supersedes subordinate Rules) and caveats its answer appropriately.

### D. Version-Aware Queries (`version_qa`)
- Tests queries referencing repealed provisions, substituted clauses, or historical amendment years.
- Verifies that the system identifies historical vs current in-force law.

### E. Summarization, Clause Analysis & Comparison
- Tests structured extraction of parties, rights, obligations, deadlines, and condition trees.
