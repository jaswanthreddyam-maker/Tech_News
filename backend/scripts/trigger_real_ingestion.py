import asyncio
import logging

from sqlalchemy import func, select

# Pre-load all models to avoid registry errors
from app.core.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def trigger_and_verify():
    async with AsyncSessionLocal() as session:
        from app.models.article import ArticleReadModel, ProcessedArticle, RawArticle

        final_raw = (await session.execute(select(func.count(RawArticle.id)).where(RawArticle.is_test_data == False))).scalar()
        final_processed = (await session.execute(select(func.count(ProcessedArticle.id)).where(ProcessedArticle.is_test_data == False))).scalar()
        final_read = (await session.execute(select(func.count(ArticleReadModel.id)).where(ArticleReadModel.is_test_data == False))).scalar()

        logger.info("--- INGESTION REPORT ---")
        logger.info(f"Total Real RawArticles: {final_raw}")
        logger.info(f"Total Real ProcessedArticles: {final_processed}")
        logger.info(f"Total Real ArticleReadModels: {final_read}")

        # Thumbnail Verification
        stmt_candidates = select(func.count(ProcessedArticle.id)).where(ProcessedArticle.is_test_data == False)
        candidates = (await session.execute(stmt_candidates)).scalar()

        stmt_downloaded = select(func.count(ProcessedArticle.id)).where(
            ProcessedArticle.is_test_data == False,
            ProcessedArticle.thumbnail_local != None
        )
        downloaded = (await session.execute(stmt_downloaded)).scalar()

        stmt_failed = select(func.count(ProcessedArticle.id)).where(
            ProcessedArticle.is_test_data == False,
            ProcessedArticle.thumbnail_status == 'failed'
        )
        failed = (await session.execute(stmt_failed)).scalar()

        rejected = candidates - downloaded - failed
        success_rate = (downloaded / candidates * 100) if candidates > 0 else 0

        logger.info("--- THUMBNAIL REPORT ---")
        logger.info(f"Thumbnail candidates (Total non-test): {candidates}")
        logger.info(f"Downloaded successfully: {downloaded}")
        logger.info(f"Failed downloads/conversions: {failed}")
        logger.info(f"No valid images found (rejected candidates): {rejected}")
        logger.info(f"Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    asyncio.run(trigger_and_verify())
