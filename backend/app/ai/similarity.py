import logging

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.article import ProcessedArticle

logger = logging.getLogger(__name__)


async def find_similar_articles(
    session: AsyncSession, article_id: int, limit: int = 10, threshold: float | None = None
) -> list[tuple[ProcessedArticle, float]]:
    """
    Finds articles semantically similar to the given article_id.

    Returns a list of tuples: (ProcessedArticle, similarity_score)
    """
    if threshold is None:
        threshold = settings.RELATED_THRESHOLD

    # 1. Fetch the target article to get its embedding
    stmt = select(ProcessedArticle).where(ProcessedArticle.id == article_id)
    result = await session.execute(stmt)
    target_article = result.scalar_one_or_none()

    if not target_article:
        logger.warning(f"Similarity Engine: Article {article_id} not found.")
        return []

    if target_article.embedding is None:
        logger.warning(f"Similarity Engine: Article {article_id} has no embedding.")
        return []

    # Cosine distance operator is `<=>`
    # Cosine Similarity = 1 - Cosine Distance
    # So we want (1 - distance) >= threshold, which means distance <= (1 - threshold)
    max_distance = 1.0 - threshold

    # 2. Find nearest neighbors
    # We exclude the target article itself.
    # We only want published articles.
    distance_col = ProcessedArticle.embedding.cosine_distance(target_article.embedding).label("distance")

    similar_stmt = (
        select(ProcessedArticle, distance_col)
        .where(
            and_(
                ProcessedArticle.id != article_id,
                ProcessedArticle.published_status == "published",
                ProcessedArticle.embedding != None,
                ProcessedArticle.embedding.cosine_distance(target_article.embedding) <= max_distance,
            )
        )
        .order_by(distance_col)
        .limit(limit)
    )

    similar_results = await session.execute(similar_stmt)

    out = []
    for row in similar_results:
        article = row.ProcessedArticle
        distance = row.distance
        similarity_score = 1.0 - float(distance)
        out.append((article, similarity_score))

    return out
