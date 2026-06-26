"""
One-time database migration script to add news ranking engine columns to processed_articles.
Usage:
    python -m app.migrations.002_add_ranking_fields
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger("tech_news.migrations.002")


async def run_migration():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    logger.info("Initializing migration 002_add_ranking_fields...")

    # Create engine using the database connection URL from settings
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        logger.info("Executing ALTER TABLE statements on processed_articles...")

        # 1. Add impact_score
        await conn.execute(
            text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS impact_score NUMERIC DEFAULT 0.0")
        )

        # 2. Add freshness_score
        await conn.execute(
            text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS freshness_score NUMERIC DEFAULT 0.0")
        )

        # 3. Add engagement_score
        await conn.execute(
            text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS engagement_score NUMERIC DEFAULT 0.0")
        )

        # 4. Add final_score
        await conn.execute(
            text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS final_score NUMERIC DEFAULT 0.0")
        )

        # 5. Add expires_at
        await conn.execute(
            text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE")
        )

        # 6. Add is_archived
        await conn.execute(
            text("ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE")
        )

        logger.info("Migration successful: Ranking engine columns added to processed_articles table.")

    await engine.dispose()
    logger.info("Migration connection disposed.")


if __name__ == "__main__":
    asyncio.run(run_migration())
