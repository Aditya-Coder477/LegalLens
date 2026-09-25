# Quality Gates & Production Readiness Criteria

## 1. Overview
The LegalLens automated Quality Gate determines whether a given build or model release meets the minimum statutory accuracy, security, and latency thresholds required for deployment.

## 2. Configurable Quality Thresholds

| Dimension | Metric | Default Threshold | Outcome on Breach |
|---|---|---|---|
| **Retrieval Quality** | Recall@10 | $\ge 0.80$ | BLOCKER (FAIL) |
| **Retrieval Quality** | MRR | $\ge 0.60$ | BLOCKER (FAIL) |
| **Retrieval Quality** | NDCG@10 | $\ge 0.70$ | WARNING (REVIEW) |
| **Grounding Faithfulness** | Unsupported Claim Rate | $\le 0.05$ (5%) | BLOCKER (FAIL) |
| **Grounding Faithfulness** | Contradiction Rate | $0.00$ (0%) | BLOCKER (FAIL) |
| **Citation Integrity** | Citation Validity Rate | $\ge 0.95$ (95%) | BLOCKER (FAIL) |
| **Security & Safety** | CRITICAL Vulnerabilities | $0$ | BLOCKER (FAIL) |
| **Security & Safety** | HIGH Vulnerabilities | $0$ | BLOCKER (FAIL) |
| **Performance** | P95 Latency | $\le 4000\text{ ms}$ | WARNING (REVIEW) |

## 3. Decision Matrix
- **PASS**: All dimensions pass thresholds with zero blockers and zero warnings.
- **REVIEW**: Tolerable deviations (e.g. latency warning or minor NDCG dip) requiring human sign-off.
- **FAIL**: Any blocker threshold breached (security vulnerability, low recall, high ungrounded rate).
