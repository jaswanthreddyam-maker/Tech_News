import sys
import os

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.grqjnmzteryrxfossice:Jaswanthreddy123456@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func, update
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel
from app.services.ingestion.pipeline import process_raw_article_to_editorial
from app.editorial.homepage_builder import HomepageBuilder
from app.services.ranking.news_ranking_engine import rank_articles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("process_raw_live")

async def main():
  async with AsyncSessionLocal() as db:
    # 1. Update status to 'fetched' for any scraped raw articles
    await db.execute(update(RawArticle).where(RawArticle.status == "scraped").values(status="fetched"))
    await db.commit()

    # 2. Query all raw articles needing processing
    res = await db.execute(select(RawArticle).where(RawArticle.status.in_(["scraped", "fetched", "ai_queued"])))
    raws = res.scalars().all()
    logger.info(f"Found {len(raws)} raw articles to process into editorial articles...")

    success = 0
    for raw in raws:
      try:
        res = await process_raw_article_to_editorial(db, raw.id)
        if res.get("status") in ["success", "duplicate"]:
          success += 1
          logger.info(f"Processed article {raw.id}: {raw.title[:40]}")
      except Exception as e:
        logger.error(f"Error processing {raw.id}: {e}")

    # Set all ProcessedArticles to published state for immediate UI feed availability
    await db.execute(
      update(ProcessedArticle)
      .where(ProcessedArticle.published_status != "published")
      .values(published_status="published", published_at=datetime.now(timezone.utc))
    )

    await db.commit()
    logger.info(f"Processed {success} articles successfully into published ProcessedArticle!")

    # 3. Run news ranking cycle to calculate scores & build homepage cache
    logger.info("Running news ranking cycle & building homepage feed cache...")
    await rank_articles(db)

    # 4. Rebuild read models & homepage builder
    await HomepageBuilder.build_homepage(db)
    logger.info("Homepage rebuild complete!")

if __name__ == "__main__":
  asyncio.run(main())
