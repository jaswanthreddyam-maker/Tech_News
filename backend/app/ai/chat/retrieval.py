import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding import EmbeddingService
from app.ai.ranking import rank_semantic_results
from app.models.article import ArticleReadModel

logger = logging.getLogger("tech_news.ai.chat.retrieval")

class RetrievalEngine:
    """
    Retrieval Pipeline for Conversational AI.
    Pipeline: Query -> Embedding -> Semantic Search -> Keyword Search -> Hybrid Ranking -> Diversity -> Top K
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def retrieve(
        self, query: str, db: AsyncSession, limit: int = 10, article_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Retrieves relevant articles for a conversation query.
        If `article_id` is provided, restricts retrieval to that article and closely related ones.
        """
        logger.info(f"Retrieving context for query: '{query}'")

        if article_id:
            # If constrained to an article, fetch that article first
            stmt = select(ArticleReadModel).where(ArticleReadModel.id == article_id)
            res = await db.execute(stmt)
            target_article = res.scalars().first()

            if not target_article:
                return []

            return [
                {
                    "type": "article",
                    "id": target_article.id,
                    "title": target_article.title,
                    "content": target_article.content or target_article.summary,
                    "url": target_article.url,
                    "score": 1.0,
                }
            ]

        try:
            vectors = await self.embedding_service.generate_embeddings([query])
            query_vector = vectors[0]
        except Exception as e:
            logger.error(f"Retrieval Engine: Failed to generate embedding: {e}")
            return []

        # pgvector Semantic Search
        distance_col = ArticleReadModel.embedding.cosine_distance(query_vector).label("distance")

        stmt = (
            select(ArticleReadModel, distance_col)
            .where(ArticleReadModel.embedding != None)
            .order_by(distance_col)
            .limit(30)  # Fetch more for re-ranking
        )

        db_results = await db.execute(stmt)

        semantic_matches = []
        for row in db_results:
            article = row.ArticleReadModel
            distance = row.distance
            semantic_score = 1.0 - float(distance)
            semantic_matches.append((article, semantic_score))

        # Hybrid Ranker
        ranked_results = rank_semantic_results(query, semantic_matches)

        # Diversity Filter (Optional: could enforce different sources or dates here)
        # For now, we take Top K
        final_results = ranked_results[:limit]

        output = []
        for rank_item in final_results:
            art = rank_item["article"]
            output.append(
                {
                    "type": "article",
                    "id": art.id,
                    "title": art.title,
                    "content": art.content or art.summary,
                    "url": art.url,
                    "score": round(rank_item["final_score"], 4),
                }
            )

        return output
