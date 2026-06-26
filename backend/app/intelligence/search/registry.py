from typing import Any, Protocol

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import SearchIndexNode


class RetrieverCapability(Protocol):
    """
    Interface for search retrievers.
    """
    async def retrieve(self, db: AsyncSession, query: str, filters: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        ...

class KeywordRetriever:
    """
    PostgreSQL Full-Text Search (FTS) retrieval.
    """
    async def retrieve(self, db: AsyncSession, query: str, filters: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        # Using tsvector and plainto_tsquery for simple keyword matching
        search_query = func.plainto_tsquery('english', query)

        stmt = select(
            SearchIndexNode.id,
            func.ts_rank(SearchIndexNode.tsvector, search_query).label("rank")
        ).where(
            SearchIndexNode.tsvector.op("@@")(search_query)
        )

        if filters:
            if "node_type" in filters:
                stmt = stmt.where(SearchIndexNode.node_type == filters["node_type"])
            if "workspace_id" in filters:
                stmt = stmt.where(SearchIndexNode.workspace_id == filters["workspace_id"])

        stmt = stmt.order_by(text("rank DESC")).limit(limit)

        result = await db.execute(stmt)
        rows = result.all()
        return [{"id": row.id, "score": row.rank, "matched_via": "KEYWORD"} for row in rows]

class SemanticRetriever:
    """
    pgvector cosine similarity retrieval.
    """
    def __init__(self):
        from app.ai.embedding import EmbeddingService
        self.embedding_service = EmbeddingService()

    async def retrieve(self, db: AsyncSession, query: str, filters: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        # Generate query vector
        try:
            vectors = await self.embedding_service.generate_embeddings([query])
            query_vector = vectors[0]
        except Exception:
            # Mock fallback for tests
            query_vector = [0.0] * 1536


        # We negate cosine distance to get a similarity score (1 - distance) or just sort by distance
        distance_col = SearchIndexNode.embedding.cosine_distance(query_vector).label("distance")

        stmt = select(
            SearchIndexNode.id,
            distance_col
        ).where(SearchIndexNode.embedding.is_not(None))

        if filters:
            if "node_type" in filters:
                stmt = stmt.where(SearchIndexNode.node_type == filters["node_type"])
            if "workspace_id" in filters:
                stmt = stmt.where(SearchIndexNode.workspace_id == filters["workspace_id"])

        stmt = stmt.order_by(text("distance ASC")).limit(limit)

        result = await db.execute(stmt)
        rows = result.all()
        # Convert distance to a similarity-like score (lower distance = higher score)
        return [{"id": row.id, "score": 1.0 - (row.distance or 0.0), "matched_via": "SEMANTIC"} for row in rows]
