# Legal Information Retrieval (IR) Evaluation

## 1. Overview
The LegalLens IR Evaluation framework benchmarks candidate retrieval performance across 5 distinct search strategies over the persistent Knowledge Base.

## 2. Retrieval Configurations Benchmarked
1. **Lexical Retrieval (FTS / BM25)**: SQLite FTS5 / PostgreSQL full-text search with exact statutory phrase matching and legal stemming.
2. **Semantic Retrieval (Dense Vectors)**: Cosine similarity over 384-dimensional dense chunk embeddings.
3. **Hybrid Retrieval (RRF)**: Reciprocal Rank Fusion combining lexical and semantic rankings with constant $k=60$.
4. **Hybrid + Local Reranker**: Hybrid candidate pool reranked using lexical term density and heading alignment.
5. **Hybrid + Query Expansion**: Query enhanced with legal synonyms, statutory definitions, and Act aliases prior to hybrid retrieval.

## 3. Standard IR Metrics Evaluated
Evaluated at $K \in [1, 3, 5, 10, 20]$:
- **Recall@K**: Proportion of ground-truth relevant chunks retrieved.
- **Precision@K**: Density of relevant chunks within the top $K$ items.
- **HitRate@K**: Frequency with which at least one relevant chunk appears in top $K$.
- **Mean Reciprocal Rank (MRR)**: Average reciprocal rank of the first relevant chunk ($1/\text{rank}$).
- **NDCG@K**: Normalized Discounted Cumulative Gain with graded relevance (0 = irrelevant, 1 = related doc, 2 = related section, 3 = exact chunk).

$$\text{DCG}@K = \sum_{i=1}^K \frac{2^{rel_i} - 1}{\log_2(i + 1)}$$

## 4. Failure Taxonomy
When retrieval fails or returns suboptimal rankings, the evaluator categorizes the root cause into one of six failure modes:
1. `vocabulary_mismatch`: Lexical miss due to semantic divergence or phrasing discrepancy.
2. `semantic_drift`: Semantic vector retrieved unrelated concepts while lexical caught keyword.
3. `missing_chunk_in_kb`: Document or statutory amendment not present in the Knowledge Base.
4. `low_similarity_rank`: Chunk present but ranked outside the top $K$ cutoff.
5. `wrong_reranker_order`: Initial hybrid rank was superior to reranked rank.
6. `chunk_boundary_cutoff`: Multi-part statutory clause severed across neighboring chunk boundaries.
