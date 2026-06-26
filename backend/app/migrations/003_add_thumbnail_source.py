"""
One-time database migration script to add thumbnail source and quality score columns to processed_articles.
Usage:
    python -m app.migrations.003_add_thumbnail_source
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger("tech_news.migrations.003")


async def run_migration():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    logger.info("Initializing migration 003_add_thumbnail_source...")

    # Create engine using the database connection URL from settings
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        logger.info("Executing ALTER TABLE statements on processed_articles...")

        # 1. Add thumbnail_source
        await conn.execute(text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_source VARCHAR(50)"))

        # 2. Add thumbnail_quality_score
        await conn.execute(
            text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_quality_score INTEGER")
        )

        logger.info("Migration successful: Thumbnail metadata columns added to processed_articles table.")

    await engine.dispose()
    logger.info("Migration connection disposed.")


if __name__ == "__main__":
    asyncio.run(run_migration())
