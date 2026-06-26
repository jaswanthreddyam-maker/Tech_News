"""
One-time database migration script to add thumbnail columns to processed_articles.
Usage:
    python -m app.migrations.001_add_thumbnails
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger("tech_news.migrations.001")


async def run_migration():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    logger.info("Initializing migration 001_add_thumbnails...")

    # Create engine using the database connection URL from settings
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        logger.info("Executing ALTER TABLE statements on processed_articles...")

        # 1. Add thumbnail_url
        await conn.execute(text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_url TEXT"))

        # 2. Add thumbnail_local
        await conn.execute(text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_local TEXT"))

        # 3. Add thumbnail_status
        await conn.execute(
            text(
                "ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_status VARCHAR(50) DEFAULT 'pending'"
            )
        )

        # 4. Add thumbnail_hash
        await conn.execute(text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_hash VARCHAR(64)"))

        logger.info("Migration successful: Columns added to processed_articles table.")

    await engine.dispose()
    logger.info("Migration connection disposed.")


if __name__ == "__main__":
    asyncio.run(run_migration())
