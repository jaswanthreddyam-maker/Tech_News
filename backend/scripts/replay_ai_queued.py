import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle
from app.tasks.summary_tasks import generate_structured_summary_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def replay_ai_queued():
    async with AsyncSessionLocal() as session:
        # We query for ProcessedArticle where status or embedding_status indicates it's queued
        # Or specifically if published_status == 'ai_queued'
        stmt = select(ProcessedArticle).where(ProcessedArticle.published_status == 'ai_queued')
        result = await session.execute(stmt)
        articles = result.scalars().all()

        logger.info(f"Found {len(articles)} ai_queued articles. Re-enqueueing...")

        for art in articles:
            generate_structured_summary_task.delay(art.id)
            logger.info(f"Enqueued AI summary for ProcessedArticle ID: {art.id}")

        logger.info("Finished re-enqueueing ai_queued articles.")

if __name__ == "__main__":
    asyncio.run(replay_ai_queued())
