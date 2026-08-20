"""
Auto-Replenishment Service (Self-Healing Article Lifecycle Engine).

Monitors inventory levels, detects expired article vacuums, and proactively
triggers RSS feed crawls and ranking rebuilds to maintain a fresh homepage.
Includes distributed debounce locking to prevent thundering-herd crawler storms.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis_client
from app.models.article import ProcessedArticle
from app.models.source import Source

logger = logging.getLogger("tech_news.ingestion.replenishment")

_in_memory_cooldown_ts: float = 0.0
COOLDOWN_SECONDS: int = 300  # 5 minutes debounce


class AutoReplenishmentService:
    @staticmethod
    async def is_in_cooldown() -> bool:
        """Check if replenishment is currently in debounce cooldown."""
        global _in_memory_cooldown_ts
        now_ts = time.time()

        if now_ts < _in_memory_cooldown_ts:
            return True

        try:
            redis = get_redis_client()
            if redis:
                val = await redis.get("ingestion:auto_replenishment:cooldown")
                if val:
                    return True
        except Exception as e:
            logger.debug(f"Redis cooldown check failed, using in-memory: {e}")

        return False

    @staticmethod
    async def set_cooldown(seconds: int = COOLDOWN_SECONDS) -> None:
        """Set the debounce cooldown in both Redis and in-memory fallback."""
        global _in_memory_cooldown_ts
        _in_memory_cooldown_ts = time.time() + seconds

        try:
            redis = get_redis_client()
            if redis:
                await redis.set("ingestion:auto_replenishment:cooldown", "1", ex=seconds)
        except Exception as e:
            logger.debug(f"Failed to set Redis cooldown key: {e}")

    @staticmethod
    async def trigger_replenishment_if_needed(db: AsyncSession | None = None, force: bool = False) -> dict:
        """
        Evaluates active article inventory. If active fresh articles are below
        the minimum floor or articles have expired, initiates debounced ingestion
        and ranking recalculation.
        """
        if db is None:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                return await AutoReplenishmentService._run_trigger_logic(session, force=force)
        return await AutoReplenishmentService._run_trigger_logic(db, force=force)

    @staticmethod
    async def _run_trigger_logic(db: AsyncSession, force: bool = False) -> dict:
        now = datetime.now(timezone.utc)
        cutoff_hours = getattr(settings, "EDITORIAL_WINDOW_HOURS", 24)
        cutoff = now - timedelta(hours=cutoff_hours)

        # 1. Check debounce cooldown
        if not force and await AutoReplenishmentService.is_in_cooldown():
            logger.info("AutoReplenishment: Ingestion cooldown active. Skipping trigger.")
            return {"triggered": False, "reason": "COOLDOWN_ACTIVE"}

        # 2. Count active, fresh published articles
        from app.services.ranking.news_ranking_engine import get_lifecycle_policy
        policy = get_lifecycle_policy()
        min_floor = int(policy.get("minimum_article_floor", 5))

        active_count_stmt = select(func.count(ProcessedArticle.id)).where(
            ProcessedArticle.is_expired == False,
            ProcessedArticle.is_archived == False,
            ProcessedArticle.published_status == "published",
            ProcessedArticle.published_at >= cutoff,
        )
        active_count_res = await db.execute(active_count_stmt)
        active_fresh_count = active_count_res.scalar() or 0

        logger.info(
            f"AutoReplenishment Check: {active_fresh_count} active fresh articles found (Floor: {min_floor}, Window: {cutoff_hours}h)."
        )

        if active_fresh_count >= min_floor and not force:
            return {"triggered": False, "reason": "INVENTORY_SUFFICIENT", "active_count": active_fresh_count}

        # 3. Acquire cooldown lock immediately before running
        await AutoReplenishmentService.set_cooldown(COOLDOWN_SECONDS)
        logger.info(
            f"AutoReplenishment TRIGGERED: Active inventory ({active_fresh_count}) below floor ({min_floor}). Initiating live crawl & replenishment."
        )

        # 4. Ensure active sources exist in DB; if 0, seed them
        sources_count_stmt = select(func.count(Source.id)).where(Source.enabled == True)
        sources_count = (await db.execute(sources_count_stmt)).scalar() or 0

        if sources_count == 0:
            logger.warning("AutoReplenishment: No enabled sources in DB. Running seed_sources.")
            await AutoReplenishmentService._seed_default_sources(db)

        # 5. Execute ingestion pipeline
        try:
            from app.services.ingestion.pipeline import run_source_ingestion_pipeline, process_raw_article_to_editorial
            from app.models.article import RawArticle

            ingest_metrics = await run_source_ingestion_pipeline(db)
            logger.info(f"AutoReplenishment Ingestion Complete: {ingest_metrics}")

            # 6. Process newly fetched raw articles to editorial ProcessedArticle & ArticleReadModel (top 15 priority batch)
            raw_stmt = select(RawArticle.id).where(RawArticle.status == "fetched").order_by(RawArticle.id.desc())
            raw_ids = (await db.execute(raw_stmt)).scalars().all()
            processed_count = 0
            for r_id in raw_ids[:15]:
                try:
                    await process_raw_article_to_editorial(db, r_id)
                    processed_count += 1
                except Exception as p_err:
                    logger.warning(f"AutoReplenishment: Failed to process RawArticle {r_id}: {p_err}")

            logger.info(f"AutoReplenishment: Processed & projected {processed_count} articles into ArticleReadModel.")

            # 7. Rebuild homepage projection and invalidate caches
            from app.editorial.homepage_builder import HomepageBuilder
            from app.services.cache_service import CacheService

            await HomepageBuilder.build_and_persist_homepage_projection(db)
            await HomepageBuilder.build_and_persist_category_desks(db)
            await CacheService.invalidate_homepage_cache(reason="auto_replenishment_ingestion")

            return {
                "triggered": True,
                "reason": "REPLENISHED",
                "metrics": ingest_metrics,
                "processed_count": processed_count,
                "active_before": active_fresh_count,
            }
        except Exception as e:
            logger.error(f"AutoReplenishment failed during ingestion execution: {e}", exc_info=True)
            return {"triggered": False, "error": str(e)}

    @staticmethod
    async def _seed_default_sources(db: AsyncSession) -> None:
        """Seeds default high-credibility RSS sources if sources table is empty."""
        default_sources = [
            {
                "name": "MIT Technology Review",
                "category": "editorial",
                "method": "rss",
                "url": "https://www.technologyreview.com/feed/",
                "credibility_score": 96,
                "crawl_interval": 900,
                "enabled": True,
            },
            {
                "name": "Google Blog",
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
                "credibility_score": 98,
                "crawl_interval": 1800,
                "enabled": True,
            },
            {
                "name": "TechCrunch",
                "category": "editorial",
                "method": "rss",
                "url": "https://techcrunch.com/feed/",
                "credibility_score": 92,
                "crawl_interval": 600,
                "enabled": True,
            },
            {
                "name": "The Verge",
                "category": "editorial",
                "method": "rss",
                "url": "https://www.theverge.com/rss/index.xml",
                "credibility_score": 90,
                "crawl_interval": 600,
                "enabled": True,
            },
            {
                "name": "Ars Technica",
                "category": "editorial",
                "method": "rss",
                "url": "https://feeds.arstechnica.com/arstechnica/index",
                "credibility_score": 88,
                "crawl_interval": 1200,
                "enabled": True,
            },
        ]

        for s_data in default_sources:
            existing = await db.execute(select(Source).where(Source.name == s_data["name"]))
            if existing.scalars().first() is None:
                src = Source(**s_data)
                db.add(src)

        await db.commit()
        logger.info("AutoReplenishment: Seeded default RSS sources.")
