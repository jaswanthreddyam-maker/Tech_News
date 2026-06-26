import asyncio
import logging

from sqlalchemy import update

from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle, RawArticle
from app.models.source import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup_synthetic_data():
    async with AsyncSessionLocal() as session:
        logger.info("Marking synthetic data as is_test_data=True...")

        # 1. Update RawArticles
        stmt_raw = update(RawArticle).where(
            RawArticle.url.like("https://synthetic.example.com%")
        ).values(is_test_data=True)
        res_raw = await session.execute(stmt_raw)
        logger.info(f"Updated {res_raw.rowcount} RawArticles.")

        # 2. Update ProcessedArticles
        stmt_pa = update(ProcessedArticle).where(
            ProcessedArticle.title.like("Synthetic Processed %")
        ).values(is_test_data=True)
        res_pa = await session.execute(stmt_pa)
        logger.info(f"Updated {res_pa.rowcount} ProcessedArticles.")

        # 3. Update ArticleReadModel
        stmt_rm = update(ArticleReadModel).where(
            ArticleReadModel.title.like("Synthetic Processed %")
        ).values(is_test_data=True)
        res_rm = await session.execute(stmt_rm)
        logger.info(f"Updated {res_rm.rowcount} ArticleReadModels.")

        # 4. We can optionally flag the "Synthetic Generator" source
        stmt_src = update(Source).where(
            Source.name == "Synthetic Generator"
        ).values(enabled=False)
        await session.execute(stmt_src)

        await session.commit()
        logger.info("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(cleanup_synthetic_data())
