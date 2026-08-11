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
            target_id = str(article_id)
            stmt = select(ArticleReadModel).where(ArticleReadModel.id == target_id)
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

        query_vector = None
        try:
            vectors = await self.embedding_service.generate_embeddings([query])
            if vectors:
                query_vector = vectors[0]
        except Exception as e:
            logger.warning(f"Retrieval Engine: Embedding generation failed: {e}. Falling back to DB keyword search.")

        semantic_matches = []
        if query_vector is not None:
            try:
                distance_col = ArticleReadModel.embedding.cosine_distance(query_vector).label("distance")
                stmt = (
                    select(ArticleReadModel, distance_col)
                    .where(ArticleReadModel.embedding != None)
                    .order_by(distance_col)
                    .limit(30)
                )
                db_results = await db.execute(stmt)
                for row in db_results:
                    article = row.ArticleReadModel
                    distance = row.distance
                    semantic_score = 1.0 - float(distance)
                    semantic_matches.append((article, semantic_score))
            except Exception as e:
                logger.warning(f"Retrieval Engine: pgvector query failed: {e}. Falling back to DB keyword search.")

        output = []
        if semantic_matches:
            ranked_results = rank_semantic_results(query, semantic_matches)
            final_results = ranked_results[:limit]
            for rank_item in final_results:
                art = rank_item["article"]
                output.append(
                    {
                        "type": "article",
                        "id": art.id,
                        "title": art.title,
                        "content": art.content or art.summary,
                        "url": art.url,
                        "source": getattr(art, "source", "Tech News Today"),
                        "score": round(rank_item["final_score"], 4),
                    }
                )

        # Fallback to DB ILIKE keyword search if vector search produced no results
        if not output:
            from sqlalchemy import or_
            query_words = [w.strip() for w in query.split() if len(w.strip()) > 2]
            if query_words:
                conditions = []
                for w in query_words[:4]:
                    conditions.append(ArticleReadModel.title.ilike(f"%{w}%"))
                    conditions.append(ArticleReadModel.summary.ilike(f"%{w}%"))
                kw_stmt = (
                    select(ArticleReadModel)
                    .where(or_(*conditions))
                    .order_by(ArticleReadModel.published_at.desc().nullslast())
                    .limit(limit)
                )
                kw_res = await db.execute(kw_stmt)
                for art in kw_res.scalars().all():
                    output.append(
                        {
                            "type": "article",
                            "id": art.id,
                            "title": art.title,
                            "content": art.content or art.summary,
                            "url": art.url,
                            "source": getattr(art, "source", "Tech News Today"),
                            "score": 0.85,
                        }
                    )

        return output
