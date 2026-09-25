# Legal Grounding & NLI Verification Benchmark

## 1. Overview
The Grounding Evaluation framework evaluates the faithfulness of generated responses against cited evidence chunks using the Phase 7 `GroundingEngine`.

## 2. Claim-Level Entailment Analysis
Every generated answer is decomposed into atomic claims. Each claim is evaluated against its cited evidence for:
- **ENTAILED**: The claim is directly supported by cited evidence text.
- **PARTIALLY_ENTAILED**: The claim is supported in principle but introduces minor extraneous terms or inferences.
- **CONTRADICTED**: The claim asserts a timeline, numerical penalty, or statutory condition opposite to or conflicting with the cited evidence.
- **UNGROUNDED**: The claim makes factual assertions without supporting evidence in the cited text.

## 3. Grounding Metrics
- **Claim Support Rate**: $\frac{\text{Entailed Claims}}{\text{Total Claims}}$ (Target: $\ge 85\%$)
- **Unsupported Claim Rate**: $\frac{\text{Ungrounded Claims}}{\text{Total Claims}}$ (Target: $\le 5\%$)
- **Contradiction Rate**: $\frac{\text{Contradicted Claims}}{\text{Total Claims}}$ (Target: $0.0\%$, zero tolerance)
- **Partial Support Rate**: $\frac{\text{Partially Entailed Claims}}{\text{Total Claims}}$
