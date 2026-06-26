import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.article import ProcessedArticle, RawArticle
from app.services.ingestion.image_helper import extract_all_candidate_urls
from app.core.event_bus import publish_event
from celery_app import download_thumbnail_task

logger = logging.getLogger(__name__)

class ThumbnailReplayService:
    @classmethod
    async def rebuild_article_thumbnail(cls, db: AsyncSession, article_id: int):
        """
        Rebuilds the thumbnail for a processed article by reloading the raw HTML,
        re-extracting candidate URLs, and enqueuing the background thumbnail task.
        """
        logger.info(f"ThumbnailReplayService: Starting replay for article_id={article_id}")

        stmt = select(ProcessedArticle).where(ProcessedArticle.id == article_id)
        res = await db.execute(stmt)
        proc_art = res.scalars().first()

        if not proc_art:
            logger.error(f"ThumbnailReplayService: ProcessedArticle {article_id} not found.")
            return False

        if not proc_art.raw_article_id:
            logger.error(f"ThumbnailReplayService: ProcessedArticle {article_id} has no raw_article_id.")
            return False

        raw_stmt = select(RawArticle).where(RawArticle.id == proc_art.raw_article_id)
        raw_res = await db.execute(raw_stmt)
        raw_art = raw_res.scalars().first()

        if not raw_art:
            logger.error(f"ThumbnailReplayService: RawArticle {proc_art.raw_article_id} not found.")
            return False

        raw_html = ""
        if raw_art.compressed_html:
            from app.services.ingestion.processor import decompress_html
            raw_html = decompress_html(raw_art.compressed_html)

        if not raw_html:
            raw_html = raw_art.clean_text or ""

        candidates = extract_all_candidate_urls(raw_html, raw_art.url)
        
        logger.info(f"ThumbnailReplayService: Extracted {len(candidates)} candidates for article_id={article_id}. Enqueuing task.")

        # Dispatch to celery task
        from app.core.config import settings
        download_thumbnail_task.delay(proc_art.id, candidates[:settings.MAX_THUMBNAIL_CANDIDATES] if candidates else [])

        # Emit audit event
        await publish_event(
            "SYSTEM",
            f"Thumbnail replay initiated for article ID {article_id}",
            "info",
            {"article_id": article_id, "candidate_count": len(candidates)}
        )

        return True
