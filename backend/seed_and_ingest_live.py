import sys
import os

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set DATABASE_URL to Supabase Transaction Pooler (port 6543)
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.grqjnmzteryrxfossice:Jaswanthreddy123456@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

import asyncio
import logging

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from app.models.article import Category
from app.services.ingestion.pipeline import run_source_ingestion_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest_live")

DEFAULT_CATEGORIES = [
  {"name": "Artificial Intelligence", "slug": "ai"},
  {"name": "Startups & Business", "slug": "startups"},
  {"name": "Software & Engineering", "slug": "software"},
  {"name": "Hardware & Gadgets", "slug": "hardware"},
  {"name": "Cybersecurity", "slug": "cybersecurity"},
  {"name": "Science & Future", "slug": "science"},
]

DEFAULT_SOURCES = [
  {"name": "TechCrunch", "category": "startups", "method": "rss", "url": "https://techcrunch.com/feed/", "is_active": True},
  {"name": "The Verge", "category": "hardware", "method": "rss", "url": "https://www.theverge.com/rss/index.xml", "is_active": True},
  {"name": "Ars Technica", "category": "technology", "method": "rss", "url": "https://feeds.arstechnica.com/arstechnica/index", "is_active": True},
  {"name": "Wired Technology", "category": "technology", "method": "rss", "url": "https://www.wired.com/feed/category/business/latest/rss", "is_active": True},
  {"name": "MIT Tech Review", "category": "ai", "method": "rss", "url": "https://www.technologyreview.com/feed/", "is_active": True},
]

async def main():
  async with AsyncSessionLocal() as session:
    logger.info("1. Seeding categories safely...")
    for cat in DEFAULT_CATEGORIES:
      existing = (await session.execute(select(Category).where(
        (Category.slug == cat["slug"]) | (Category.name == cat["name"])
      ))).scalars().first()
      if not existing:
        session.add(Category(name=cat["name"], slug=cat["slug"]))
        await session.commit()

    logger.info("2. Seeding RSS sources safely...")
    for src in DEFAULT_SOURCES:
      existing = (await session.execute(select(Source).where(
        (Source.name == src["name"]) | (Source.url == src["url"])
      ))).scalars().first()
      if not existing:
        session.add(Source(
          name=src["name"],
          category=src["category"],
          method=src["method"],
          url=src["url"],
          enabled=True,
          parser_version="1.0"
        ))
        await session.commit()

    logger.info("3. Executing live ingestion pipeline...")
    metrics = await run_source_ingestion_pipeline(session)
    logger.info(f"Ingestion metrics: {metrics}")

if __name__ == "__main__":
  asyncio.run(main())
