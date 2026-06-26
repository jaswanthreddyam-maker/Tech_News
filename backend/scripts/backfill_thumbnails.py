import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle
from app.services.ingestion.image_helper import extract_all_candidate_urls
from app.services.ingestion.processor import decompress_html
from celery_app import download_thumbnail_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def backfill_thumbnails():
    async with AsyncSessionLocal() as session:
        # We need ProcessedArticle where thumbnail_local is NULL
        stmt = select(ProcessedArticle).options(
            selectinload(ProcessedArticle.raw_article)
        ).where(ProcessedArticle.thumbnail_local.is_(None))
        result = await session.execute(stmt)
        articles = result.scalars().all()

        logger.info(f"Found {len(articles)} articles missing thumbnail_local. Backfilling...")

        for art in articles:
            if not art.raw_article:
                continue

            raw_html = ""
            if art.raw_article.compressed_html:
                raw_html = decompress_html(art.raw_article.compressed_html)
            elif art.raw_article.clean_text:
                raw_html = art.raw_article.clean_text

            candidates = extract_all_candidate_urls(raw_html, art.raw_article.url)
            if candidates:
                download_thumbnail_task.delay(art.id, candidates[:4])
                logger.info(f"Enqueued backfill thumbnail task for ProcessedArticle ID: {art.id}")
            else:
                logger.info(f"No candidates found for ProcessedArticle ID: {art.id}")
                art.thumbnail_status = "failed"
                art.thumbnail_url = "fallback"

        await session.commit()
        logger.info("Finished backfilling thumbnails.")

if __name__ == "__main__":
    asyncio.run(backfill_thumbnails())
