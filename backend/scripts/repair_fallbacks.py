import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle
from app.services.ingestion.thumbnail_service import ThumbnailUpdatedApplicationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def repair_fallbacks():
    async with AsyncSessionLocal() as session:
        logger.info("Starting fallback thumbnail path repair...")

        from app.models.article import ArticleReadModel

        # 1. Update processed_articles based on articles read model
        stmt = select(ArticleReadModel).where(
            ArticleReadModel.thumbnail_local == "/api/v1/uploads/thumbnails/fallback-news.webp"
        )
        res = await session.execute(stmt)
        read_models = res.scalars().all()

        articles = []
        for rm in read_models:
            # Reconstruct ProcessedArticle ID from artifact ID (e.g. editorial_5)
            try:
                art_id = int(rm.id.split("_")[1])
                # Let's get the ProcessedArticle to make sure it exists
                pa = await session.get(ProcessedArticle, art_id)
                if pa:
                    articles.append(pa)
            except Exception as e:
                logger.error(f"Failed to process read model {rm.id}: {e}")

        if not articles:
            logger.info("No fallback paths found to repair.")
            return

        logger.info(f"Found {len(articles)} articles with incorrect fallback paths.")

        for art in articles:
            # We can use ThumbnailUpdatedApplicationService to emit the domain event natively.
            await ThumbnailUpdatedApplicationService.finalize_thumbnail_update(
                db=session,
                article_id=art.id,
                thumbnail_url="/images/fallback-news.webp",
                thumbnail_local="/images/fallback-news.webp",
                thumbnail_hash="fallback",
                thumbnail_source="fallback",
                candidate_count=art.candidate_count,
                winner_pass="fallback",
                thumbnail_score=0
            )

        # 2. Although we emitted events, the repair script might want to force sync immediately
        # OR we can just let celery process the outbox. But since we are repairing, we can
        # optionally just let the outbox events be processed by the worker naturally, or trigger them.
        logger.info("Triggering Projection Repair Service to immediately execute pending projections...")

        # Wait, if we use ProjectionRepairService, it processes the entire read model for all published articles.
        # It's better to just process the EventOutbox right here to make it fast and deterministic.
        from app.tasks.distribution_tasks import _async_process_event_outbox_task
        await _async_process_event_outbox_task()

        logger.info("Fallback repair complete.")

if __name__ == "__main__":
    asyncio.run(repair_fallbacks())
