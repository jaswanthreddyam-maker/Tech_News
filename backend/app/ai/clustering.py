import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.similarity import find_similar_articles
from app.core.config import settings
from app.models.article import ProcessedArticle

logger = logging.getLogger(__name__)


async def assign_to_cluster(session: AsyncSession, article: ProcessedArticle) -> None:
    """
    Lightweight Story Clustering.
    Finds nearest neighbors for a newly embedded article.
    If similarity > threshold, joins their cluster.
    Otherwise, creates a new cluster.
    """
    if article.embedding is None:
        logger.warning(f"Clustering: Article {article.id} has no embedding. Cannot cluster.")
        return

    # Find the nearest neighbor (limit 1)
    # We use a very high threshold for clustering to ensure it's the exact same story
    similar_results = await find_similar_articles(
        session=session, article_id=article.id, limit=1, threshold=settings.CLUSTER_THRESHOLD
    )

    now = datetime.now(timezone.utc)

    if similar_results:
        nearest_neighbor, similarity_score = similar_results[0]
        from sqlalchemy import update

        # If the nearest neighbor already has a cluster, join it
        if nearest_neighbor.cluster_id:
            article.cluster_id = nearest_neighbor.cluster_id
            article.cluster_score = similarity_score
            new_size = nearest_neighbor.cluster_size + 1
            article.cluster_size = new_size

            # Update existing cluster members
            stmt = (
                update(ProcessedArticle)
                .where(ProcessedArticle.cluster_id == nearest_neighbor.cluster_id)
                .values(cluster_size=new_size)
            )
            await session.execute(stmt)
            logger.info(
                f"Clustering: Article {article.id} joined cluster {article.cluster_id} (Sim: {similarity_score:.4f}, Size: {new_size})"
            )
        else:
            # Create a new cluster for both
            new_cluster_id = str(uuid.uuid4())
            nearest_neighbor.cluster_id = new_cluster_id
            nearest_neighbor.cluster_updated_at = now
            nearest_neighbor.cluster_size = 2

            article.cluster_id = new_cluster_id
            article.cluster_score = similarity_score
            article.cluster_size = 2
            logger.info(
                f"Clustering: Article {article.id} joined cluster {article.cluster_id} (Sim: {similarity_score:.4f}, Size: 2)"
            )
    else:
        # No strong matches, create a new cluster
        article.cluster_id = str(uuid.uuid4())
        article.cluster_score = 1.0  # 100% match with itself
        logger.info(f"Clustering: Article {article.id} started new cluster {article.cluster_id}")

    article.cluster_updated_at = now
