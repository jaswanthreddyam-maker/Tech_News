# Embedding Architecture

## 1. Overview
In Phase 5, the system introduces a vector embedding pipeline to enable semantic similarity search and recommendation engines for news articles. 

Unlike the AI summarization pipeline (which blocks article enrichment), the **Embedding Generation is entirely asynchronous**. It runs as a detached Celery background process, ensuring that raw content generation and publication are never delayed by vector infrastructure issues.

## 2. Infrastructure Components

- **Database**: PostgreSQL with `pgvector` extension.
- **Model**: Configurable via `.env` (`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`), defaulting to `openai` `text-embedding-3-small` (1536 dims).
- **Index Strategy**: HNSW (Hierarchical Navigable Small World) for sub-millisecond Approximate Nearest Neighbor (ANN) search over millions of rows.
- **Queue**: Dedicated Celery queue (`embedding_processing`) with high retry thresholds.

## 3. Workflow Lifecycle

1. **Article Processing**: The core crawler/pipeline enriches the article, stores it in `processed_articles`, and marks `embedding_status = "pending"`. The article is now considered **published** and available to users.
2. **Task Trigger**: Immediately upon saving the processed article, `process_embedding_task.delay(article.id)` is fired.
3. **Deduplication Check**: The `EmbeddingService` generates an `embedding_hash` (e.g., SHA256 of the concatenated title + content). If this hash matches `ProcessedArticle.embedding_hash`, vector generation is skipped to avoid duplicate API charging.
4. **API Call**: The provider generates the vector embedding.
5. **Storage**: The vector is stored in `ProcessedArticle.embedding`, and `embedding_status` is updated to `"completed"`.

## 4. Error Handling and Resilience

- **Retry Strategy**: The Celery task allows up to 5 retries with exponential backoff for transient provider failures.
- **Circuit Breaking**: The embedding API calls use the same Redis-backed Circuit Breaker design as Phase 4 to prevent budget explosions or cascading failures.
- **Missing `pgvector`**: On environments lacking `pgvector` support (e.g. lightweight dev setups), the health checks report `Embedding Disabled` rather than crashing the primary app. The schema relies on SQLAlchemy `UserDefinedType` or standard vector mappings to fail gracefully if the extension isn't loaded correctly.

## 5. Next Steps (Phase 5B & 5C)
- Implementing standard `cosine_distance` ( `<=>` ) operations in SQLAlchemy to query semantic similarity.
- Building the "Related Articles" endpoint in the frontend, exposing a GraphQL/REST route that retrieves top-K neighbors.
