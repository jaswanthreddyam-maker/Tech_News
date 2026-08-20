import asyncio
import os
import sys
import logging
from datetime import datetime, timezone
from sqlalchemy import text, select, func

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flush_and_crawl")

async def main():
    logger.info("=== STEP 1: INITIALIZING ENVIRONMENT ===")
    from app.core.database import AsyncSessionLocal
    from app.models.source import Source
    from app.models.article import Category, RawArticle, ProcessedArticle, ArticleReadModel
    from app.models.projection import HomepageProjection, CategoryDeskProjection

    async with AsyncSessionLocal() as db:
        logger.info("=== STEP 2: CLEARING EXISTING POSTGRESQL TABLES ===")
        # Terminate any hanging locks
        try:
            await db.execute(text("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = 'tech_news_today' AND pid != pg_backend_pid();
            """))
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not terminate backends: {e}")

        # Truncate tables cleanly
        truncate_sql = """
            TRUNCATE TABLE 
                processed_articles, 
                raw_articles, 
                articles, 
                homepage_projections, 
                category_desk_projections, 
                tnt_article_entities, 
                tnt_article_topics, 
                event_outbox, 
                stories, 
                story_health_projections, 
                ai_job_history
            RESTART IDENTITY CASCADE;
        """
        await db.execute(text(truncate_sql))
        await db.commit()
        logger.info("Successfully truncated all article and projection tables.")

        # Ensure categories exist
        logger.info("=== STEP 3: SEEDING CANONICAL CATEGORIES ===")
        categories_data = [
            {"name": "Artificial Intelligence", "slug": "artificial-intelligence"},
            {"name": "Hardware & Devices", "slug": "hardware"},
            {"name": "Software & DevOps", "slug": "software"},
            {"name": "Cybersecurity", "slug": "cybersecurity"},
            {"name": "Science & Quantum", "slug": "science"},
            {"name": "Startups & Venture", "slug": "startups"},
            {"name": "Big Tech & Policy", "slug": "policy"},
            {"name": "Web3 & Crypto", "slug": "crypto"},
        ]
        for c in categories_data:
            existing = (await db.execute(select(Category).where(Category.slug == c["slug"]))).scalars().first()
            if not existing:
                db.add(Category(name=c["name"], slug=c["slug"]))
        await db.commit()

        # Seed high-quality active RSS sources
        logger.info("=== STEP 4: SEEDING LIVE RSS NEWS SOURCES ===")
        live_sources = [
            {
                "name": "TechCrunch",
                "category": "editorial",
                "method": "rss",
                "url": "https://techcrunch.com/feed/",
                "credibility_score": 95,
                "crawl_interval": 600,
                "enabled": True,
            },
            {
                "name": "The Verge",
                "category": "editorial",
                "method": "rss",
                "url": "https://www.theverge.com/rss/index.xml",
                "credibility_score": 94,
                "crawl_interval": 600,
                "enabled": True,
            },
            {
                "name": "Ars Technica",
                "category": "editorial",
                "method": "rss",
                "url": "https://feeds.arstechnica.com/arstechnica/index",
                "credibility_score": 93,
                "crawl_interval": 900,
                "enabled": True,
            },
            {
                "name": "MIT Technology Review",
                "category": "academic",
                "method": "rss",
                "url": "https://www.technologyreview.com/feed/",
                "credibility_score": 98,
                "crawl_interval": 900,
                "enabled": True,
            },
            {
                "name": "Wired Tech",
                "category": "editorial",
                "method": "rss",
                "url": "https://www.wired.com/feed/rss",
                "credibility_score": 92,
                "crawl_interval": 900,
                "enabled": True,
            },
            {
                "name": "VentureBeat",
                "category": "editorial",
                "method": "rss",
                "url": "https://venturebeat.com/feed/",
                "credibility_score": 90,
                "crawl_interval": 900,
                "enabled": True,
            },
            {
                "name": "Google Official Blog",
                "category": "official",
                "method": "rss",
                "url": "https://blog.google/rss/",
                "credibility_score": 98,
                "crawl_interval": 900,
                "enabled": True,
            },
            {
                "name": "NVIDIA AI Blog",
                "category": "official",
                "method": "rss",
                "url": "https://blogs.nvidia.com/feed/",
                "credibility_score": 97,
                "crawl_interval": 900,
                "enabled": True,
            },
        ]
        for s in live_sources:
            existing = (await db.execute(select(Source).where(Source.url == s["url"]))).scalars().first()
            if not existing:
                db.add(Source(**s))
            else:
                existing.enabled = True
        await db.commit()
        logger.info(f"Sources initialized: {len(live_sources)} sources active.")

        logger.info("=== STEP 5: FLUSHING REDIS CACHE ===")
        try:
            from app.core.redis import get_redis_client
            redis = get_redis_client()
            if redis:
                await redis.flushdb()
                logger.info("Redis cache flushed completely.")
        except Exception as r_err:
            logger.warning(f"Could not flush Redis: {r_err}")

        logger.info("=== STEP 6: EXECUTING LIVE CRAWL AGAINST REAL RSS FEEDS ===")
        from app.services.ingestion.pipeline import run_source_ingestion_pipeline, process_raw_article_to_editorial
        ingest_metrics = await run_source_ingestion_pipeline(db)
        logger.info(f"Live Ingestion Completed: {ingest_metrics}")

        # Check raw articles count
        raw_count = (await db.execute(select(func.count(RawArticle.id)))).scalar() or 0
        logger.info(f"Raw articles scraped: {raw_count}")

        logger.info("=== STEP 7: RUNNING EDITORIAL PROCESSING & SCORING PIPELINE ===")
        raw_stmt = select(RawArticle.id).where(RawArticle.status.in_(["scraped", "fetched", "ai_queued"])).order_by(RawArticle.id.asc())
        raw_ids = (await db.execute(raw_stmt)).scalars().all()
        
        processed_count = 0
        for r_id in raw_ids:
            try:
                res = await process_raw_article_to_editorial(db, r_id)
                if res.get("status") == "success":
                    processed_count += 1
            except Exception as e:
                logger.warning(f"Failed processing RawArticle {r_id}: {e}")

        await db.commit()
        logger.info(f"Successfully transformed {processed_count} raw articles into ProcessedArticle & ArticleReadModel.")

        logger.info("=== STEP 8: REBUILDING HOMEPAGE & CATEGORY DESK PROJECTIONS ===")
        from app.editorial.homepage_builder import HomepageBuilder
        from app.services.cache_service import CacheService

        homepage_articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
        category_desks = await HomepageBuilder.build_and_persist_category_desks(db)
        await CacheService.invalidate_homepage_cache(reason="full_database_flush_and_crawl")

        logger.info(f"Homepage built with {len(homepage_articles)} top-ranked articles.")
        desks_count = len(category_desks) if category_desks else "all"
        logger.info(f"Category desks built: {desks_count} desks populated.")

        print("\n=======================================================")
        print("          LIVE HOMEPAGE ARTICLES JUST FETCHED          ")
        print("=======================================================")
        for idx, art in enumerate(homepage_articles, start=1):
            print(f"[{idx}] {art.title}")
            print(f"    Source: {art.source_name or art.source} | Score: {art.final_score:.1f} | Published: {art.published_at}")
            print(f"    URL: {art.url}\n")

if __name__ == "__main__":
    asyncio.run(main())
