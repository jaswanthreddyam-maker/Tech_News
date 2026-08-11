import sys
import os

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.grqjnmzteryrxfossice:Jaswanthreddy123456@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

import asyncio
import logging
import re
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, ArticleReadModel, RawArticle
from app.services.ingestion.image_helper import extract_all_candidate_urls
from app.services.ingestion.processor import decompress_html
from app.editorial.homepage_builder import HomepageBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("populate_thumbnails_live")

# Unsplash / Tech high-res fallback image curated bank per domain / category
FALLBACK_IMAGES = {
  "ai": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80",
  "technology": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
  "hardware": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80",
  "software": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1200&q=80",
  "cybersecurity": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=1200&q=80",
  "startups": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80",
  "default": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80"
}

async def main():
  async with AsyncSessionLocal() as session:
    stmt = select(ProcessedArticle).options(
      selectinload(ProcessedArticle.raw_article),
      selectinload(ProcessedArticle.category)
    )
    res = await session.execute(stmt)
    articles = res.scalars().all()

    logger.info(f"Assigning high-res thumbnails for {len(articles)} processed articles...")
    updated_count = 0

    for art in articles:
      image_url = None
      if art.raw_article:
        raw_html = ""
        if art.raw_article.compressed_html:
          raw_html = decompress_html(art.raw_article.compressed_html)
        elif art.raw_article.clean_text:
          raw_html = art.raw_article.clean_text

        candidates = extract_all_candidate_urls(raw_html, art.raw_article.url)
        if candidates:
          image_url = candidates[0].get("url")

      if not image_url or "logo" in image_url.lower() or "icon" in image_url.lower():
        cat = (art.category.slug if art.category else "default").lower()
        image_url = FALLBACK_IMAGES.get(cat, FALLBACK_IMAGES["default"])

      art.thumbnail_url = image_url
      art.thumbnail_local = image_url
      art.thumbnail_status = "success"
      updated_count += 1

    await session.commit()
    logger.info(f"Successfully populated thumbnails for {updated_count} ProcessedArticles!")

    # Synchronize ArticleReadModel thumbnail_url
    logger.info("Synchronizing ArticleReadModel records...")
    stmt_read = select(ArticleReadModel)
    res_read = await session.execute(stmt_read)
    read_models = res_read.scalars().all()

    # Map processed articles by string id to match ArticleReadModel.id
    proc_map = {str(a.id): a for a in articles}
    for rm in read_models:
      pa = proc_map.get(str(rm.id))
      if pa and pa.thumbnail_url:
        rm.thumbnail_url = pa.thumbnail_url

    await session.commit()

    # Rebuild & persist homepage projection with thumbnails
    from app.core.redis import get_redis_client
    await HomepageBuilder.build_and_persist_homepage_projection(session)

    try:
      redis = get_redis_client()
      if redis:
        await redis.delete("editorial:v1:homepage_ranked_ids")
        await redis.delete("homepage:v1:curated_projection")
        await redis.delete("editorial:v2:homepage_cards_full_json")
        logger.info("Cleared Redis cache keys!")
    except Exception as e:
      logger.warning(f"Redis cache clear note: {e}")

    logger.info("Homepage rebuilt and persisted with full thumbnails!")

if __name__ == "__main__":
  asyncio.run(main())
