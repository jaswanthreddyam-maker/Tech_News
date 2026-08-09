import sys
import os
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel
from app.services.ingestion.pipeline import process_raw_article_to_editorial
from app.editorial.homepage_builder import HomepageBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("process_fetched_articles")

async def run_recovery():
    logger.info("Starting deterministic recovery batch for stranded 'fetched' RawArticles...")

    async with AsyncSessionLocal() as db:
        # Pre-execution DB counts
        raw_total_pre = (await db.execute(select(func.count(RawArticle.id)))).scalar() or 0
        raw_fetched_pre = (await db.execute(select(func.count(RawArticle.id)).where(RawArticle.status == "fetched"))).scalar() or 0
        raw_queued_pre = (await db.execute(select(func.count(RawArticle.id)).where(RawArticle.status == "ai_queued"))).scalar() or 0
        proc_pre = (await db.execute(select(func.count(ProcessedArticle.id)))).scalar() or 0
        read_pre = (await db.execute(select(func.count(ArticleReadModel.id)))).scalar() or 0

        logger.info(f"PRE-BATCH COUNTS: Raw Total={raw_total_pre}, Fetched Pending={raw_fetched_pre}, Queued Pending={raw_queued_pre}, Processed={proc_pre}, ReadModel={read_pre}")

        # Fetch candidate raw articles in 'fetched' or 'ai_queued' state
        stmt = (
            select(RawArticle)
            .where(RawArticle.status.in_(["fetched", "ai_queued"]))
            .order_by(RawArticle.scraped_at.desc())
        )
        res = await db.execute(stmt)
        candidates = res.scalars().all()

        logger.info(f"Found {len(candidates)} raw articles in 'fetched'/'ai_queued' state awaiting processing.")

        processed_count = 0
        dead_letter_count = 0
        error_count = 0

        # Operational batching loop
        for raw in candidates:
            logger.info(f"Processing RawArticle ID {raw.id}: '{raw.title[:50]}'")
            try:
                result = await process_raw_article_to_editorial(db, raw.id)
                status = result.get("status")
                if status == "success":
                    processed_count += 1
                elif status == "dead_letter":
                    dead_letter_count += 1
                else:
                    logger.warning(f"Unexpected status for RawArticle {raw.id}: {result}")
            except Exception as e:
                logger.error(f"Transient or unexpected error processing RawArticle {raw.id}: {e}", exc_info=True)
                raw.retry_count = (raw.retry_count or 0) + 1
                raw.last_retry_at = datetime.now(timezone.utc)
                if raw.retry_count >= 3:
                    raw.status = "dead_letter"
                    raw.dead_letter_reason = f"Exhausted max retries (3): {e!s}"
                    raw.dead_letter_at = datetime.now(timezone.utc)
                    dead_letter_count += 1
                    logger.error(f"RawArticle ID {raw.id} marked as dead_letter due to retry exhaustion.")
                else:
                    error_count += 1
                await db.commit()

        # Rebuild projections
        logger.info("Rebuilding Homepage & Category Desk Projections...")
        await HomepageBuilder.build_and_persist_homepage_projection(db)
        await HomepageBuilder.build_and_persist_category_desks(db)

        # Post-execution DB counts
        raw_total_post = (await db.execute(select(func.count(RawArticle.id)))).scalar() or 0
        raw_fetched_post = (await db.execute(select(func.count(RawArticle.id)).where(RawArticle.status == "fetched"))).scalar() or 0
        raw_queued_post = (await db.execute(select(func.count(RawArticle.id)).where(RawArticle.status == "ai_queued"))).scalar() or 0
        proc_post = (await db.execute(select(func.count(ProcessedArticle.id)))).scalar() or 0
        read_post = (await db.execute(select(func.count(ArticleReadModel.id)))).scalar() or 0

        # Detailed RawArticle status breakdown
        status_breakdown = (await db.execute(
            select(RawArticle.status, func.count(RawArticle.id)).group_by(RawArticle.status)
        )).all()

        print("\n==========================================")
        print("     RECOVERY BATCH EXECUTION REPORT      ")
        print("==========================================")
        print(f"Processed Successfully : {processed_count}")
        print(f"Dead Lettered          : {dead_letter_count}")
        print(f"Transient Errors       : {error_count}")
        print("\n--- DATABASE STATUS BREAKDOWN ---")
        print(f"Raw Articles Total    : {raw_total_post}")
        print(f"Pending Fetched       : {raw_fetched_post}")
        print(f"Pending Queued        : {raw_queued_post}")
        print(f"ProcessedArticles     : {proc_post}")
        print(f"ArticleReadModels     : {read_post}")
        print("\nRawArticle Status Distribution:")
        for st, cnt in status_breakdown:
            print(f"  - {st}: {cnt}")
        print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(run_recovery())
