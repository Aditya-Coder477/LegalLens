# LegalLens IR Retrieval Benchmark Report

## Strategy Comparison Table

| Strategy | Recall@1 | Recall@5 | Recall@10 | Precision@10 | MRR | NDCG@10 | Avg Latency (ms) |
|---|---|---|---|---|---|---|---|
| **lexical** | 0.138 | 0.602 | 0.828 | 0.772 | 1.000 | 0.997 | 268.4 |
| **semantic** | 0.605 | 0.655 | 0.850 | 0.056 | 0.129 | 0.153 | 978.2 |
| **hybrid** | 0.046 | 0.284 | 0.643 | 0.452 | 0.697 | 0.546 | 562.0 |
| **hybrid_rerank** | 0.103 | 0.643 | 1.000 | 0.268 | 0.570 | 0.653 | 566.6 |
| **hybrid_expansion** | 0.136 | 0.549 | 1.000 | 0.336 | 0.658 | 0.691 | 566.7 |

## Failure Taxonomy
