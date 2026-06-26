# Semantic Architecture

This document serves as the definitive reference for the semantic subsystem in the Tech News Platform (introduced in Phase 5B).

## 1. Embedding Lifecycle
Every `ProcessedArticle` tracks its embedding generation state via the `embedding_status` column. 
The explicit lifecycle is:
1. `pending`: Initial state upon article creation.
2. `queued`: Celery embedding task enqueued.
3. `processing`: Celery worker actively generating vectors.
4. `completed`: Vectors generated and stored.
5. `failed`: Celery task exhausted retries (monitored via dead letter metrics).
6. `stale`: Content was updated, necessitating re-embedding.

## 2. pgvector & HNSW Indexing
- The embedding database leverages PostgreSQL with the `pgvector` extension.
- **Indexing**: Uses an HNSW (Hierarchical Navigable Small World) index configured for cosine distance `(<=>)`.
- Dimensions are dynamically configured via `EMBEDDING_DIMENSIONS`.

## 3. Semantic Search
Semantic search calculates similarity using cosine similarity. Given a search query `q`:
1. Generate an embedding vector `v` for the query `q`.
2. Query `SELECT * FROM processed_articles ORDER BY embedding <=> v LIMIT K;`.

## 4. Hybrid Ranking Algorithm
Semantic similarity alone may bubble up stale or unreliable news. Hybrid ranking weights multiple signals:
- **0.45 Semantic Similarity**: Pure vector cosine distance.
- **0.20 Freshness**: Exponential decay based on `published_at`.
- **0.15 Source Credibility**: Moving average of source reliability.
- **0.10 Popularity**: Based on user engagement or estimated view limits.
- **0.10 Keyword Overlap**: BM25 / TF-IDF style exact keyword boosting.

## 5. Phase 5B Implementation Sequence
1. **Step 1: Similarity Engine** - Core logic for vector cosine similarity and Top-K retrieval.
2. **Step 2: Related Articles API** - `GET /api/v1/articles/{id}/related` endpoint.
3. **Step 3: Semantic Search** - `GET /api/v1/search?q=...` leveraging Hybrid Ranking.
4. **Step 4: Hybrid Ranking** - Applying the 45/20/15/10/10 weighting function over PG vectors.
5. **Step 5: Story Clustering** - Grouping duplicate/perspectival stories (e.g., Reuters, TechCrunch, The Verge) into single cluster events.
6. **Step 6: Recommendations** - Exposing "Readers also viewed" & "Continue reading" blocks.

## 6. Optimization Strategies
- **Caching**: Frequently requested queries and standard related-article sets are cached in Redis.
- **Re-embedding**: Automatically transitions to `stale` on major editorial content changes, debounced by a background task.
