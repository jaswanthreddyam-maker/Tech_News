"""
Batch migration script to retrofit existing articles with thumbnails.
Enqueues missing downloads to the Celery background worker.
Usage:
    python -m app.core.migrate_thumbnails
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from agents.ingestion.html_agent import HTMLAgent
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle
from app.services.ingestion.image_helper import extract_all_candidate_urls
from app.services.ingestion.processor import decompress_html
from app.services.ingestion.utils import compress_content
from celery_app import download_thumbnail_task

logger = logging.getLogger("tech_news.migrate_thumbnails")

HTML_REFETCH_TIMEOUT = 15


async def run_migration():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    logger.info("Starting batch thumbnail migration job...")

    html_agent = HTMLAgent()

    async with AsyncSessionLocal() as db:
        # Fetch articles that do not have a completed thumbnail download
        stmt = (
            select(ProcessedArticle)
            .options(selectinload(ProcessedArticle.raw_article))
            .where(ProcessedArticle.thumbnail_local == None)
        )
        res = await db.execute(stmt)
        articles = res.scalars().all()

        if not articles:
            logger.info("All articles have completed thumbnails. No migration needed.")
            await html_agent.shutdown()
            return

        logger.info(f"Found {len(articles)} articles missing thumbnails. Beginning validation and refetch checks...")

        # Statistics
        scanned_count = len(articles)
        skipped_count = 0
        refetched_count = 0
        refetch_success = 0
        refetch_failed = 0
        candidates_found_count = 0
        fallbacks_remaining = 0

        for art in articles:
            if not art.raw_article:
                logger.warning(f"ProcessedArticle ID {art.id} has no linked RawArticle. Skipping.")
                scanned_count -= 1
                continue

            raw_art = art.raw_article

            # Decompress HTML to check length
            raw_html = ""
            if raw_art.compressed_html:
                try:
                    raw_html = decompress_html(raw_art.compressed_html)
                except Exception as de_err:
                    logger.warning(f"Failed to decompress HTML for RawArticle ID {raw_art.id}: {de_err}")

            if not raw_html:
                raw_html = raw_art.clean_text or ""

            html_length = len(raw_html)

            # Refetch logic if HTML is invalid/incomplete (< 10000 characters)
            if html_length < 10000:
                logger.info(
                    f"Re-fetching raw HTML for RawArticle ID {raw_art.id} (current length: {html_length}) from {raw_art.url}"
                )
                refetched_count += 1
                extracted = None
                try:
                    extracted = await html_agent.extract_article(raw_art.url, timeout=HTML_REFETCH_TIMEOUT)
                except Exception as fetch_err:
                    logger.error(f"Error fetching URL {raw_art.url} for RawArticle ID {raw_art.id}: {fetch_err}")

                if extracted and extracted.get("raw_html"):
                    new_raw_html = extracted["raw_html"]
                    raw_art.compressed_html = compress_content(new_raw_html)
                    raw_art.html_refetched_at = datetime.now(timezone.utc)
                    raw_html = new_raw_html
                    refetch_success += 1
                    logger.info(
                        f"Successfully refetched and saved HTML for RawArticle ID {raw_art.id} (new length: {len(new_raw_html)})"
                    )
                else:
                    refetch_failed += 1
                    logger.warning(
                        f"Refetch failed for RawArticle ID {raw_art.id}. Using existing raw_html/clean_text."
                    )
            else:
                skipped_count += 1
                logger.info(
                    f"Skipping re-fetch for RawArticle ID {raw_art.id} (already valid HTML length: {html_length})"
                )

            # Extract candidates using correct raw HTML
            candidates = extract_all_candidate_urls(raw_html, raw_art.url)

            # Logging HTML length and candidates found
            logger.info(
                "%s | html=%d | candidates=%d",
                raw_art.id,
                len(raw_html),
                len(candidates),
            )

            if candidates:
                art.thumbnail_url = candidates[0]["url"]
                candidates_found_count += 1
            else:
                art.thumbnail_url = "/api/v1/uploads/thumbnails/fallback-news.webp"
                fallbacks_remaining += 1

            # TRANSACTION SAFETY: Commit HTML updates and art state first
            await db.commit()

            # Enqueue the Celery download task only AFTER transaction commits
            download_thumbnail_task.delay(art.id, candidates)
            logger.info(f" - Enqueued download task for article ID {art.id} ({len(candidates)} candidates)")

        logger.info("=" * 50)
        logger.info("MIGRATION STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Articles scanned: {scanned_count}")
        logger.info(f"Articles skipped (already valid HTML): {skipped_count}")
        logger.info(f"Articles refetched: {refetched_count}")
        logger.info(f"Refetch success: {refetch_success}")
        logger.info(f"Refetch failed: {refetch_failed}")
        logger.info(f"Candidates Found: {candidates_found_count}")
        logger.info(f"Fallbacks Remaining: {fallbacks_remaining}")
        logger.info("=" * 50)

    await html_agent.shutdown()


if __name__ == "__main__":
    asyncio.run(run_migration())
