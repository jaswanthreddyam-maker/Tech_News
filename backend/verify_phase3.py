import asyncio
import logging

from app.api.v1.routes.admin import list_admin_sources, toggle_admin_source
from app.api.v1.routes.search import search_articles
from app.api.v1.routes.telemetry import get_sources_telemetry, get_trend_explorer
from app.core.database import AsyncSessionLocal

# Setup base logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_phase3")


async def verify_search_filters():
    logger.info("--- 1. Verifying Dynamic Search & Filters ---")
    async with AsyncSessionLocal() as db:
        # Fetch standard search
        res = await search_articles(q="openai", limit=5, db=db)
        logger.info(f"FTS Query 'openai' Results Count: {len(res.data)}")
        for i, art in enumerate(res.data):
            logger.info(
                f"  [{i + 1}] Title: {art['title'][:40]} | Source: {art['source']} | Cat: {art['source_category']}"
            )

        # Fetch filter by category
        res_cat = await search_articles(q="openai", source_category="official", limit=5, db=db)
        logger.info(f"FTS Category 'official' Results Count: {len(res_cat.data)}")

        # Fetch sorted by freshness
        res_fresh = await search_articles(q="openai", sort_by="freshness", limit=5, db=db)
        logger.info(f"FTS Sorted by Freshness Count: {len(res_fresh.data)}")


async def verify_telemetry_sources():
    logger.info("\n--- 2. Verifying Sources Telemetry API ---")
    async with AsyncSessionLocal() as db:
        res = await get_sources_telemetry(db=db)
        logger.info(f"Registered Sources Count: {len(res.data)}")
        for src in res.data[:3]:
            logger.info(
                f"  Source: '{src['name']}' | Category: {src['category']} | Latency: {src['avg_latency_ms']}ms | Reliability: {src['reliability_score']}%"
            )


async def verify_trend_explorer():
    logger.info("\n--- 3. Verifying Trend Explorer Intelligence Briefing ---")
    async with AsyncSessionLocal() as db:
        # Retrieve a dynamic trend topic or fall back to General
        res_sources = await get_sources_telemetry(db=db)
        topic = "ai"
        if res_sources.data:
            topic = res_sources.data[0]["category"]

        res = await get_trend_explorer(topic=topic, db=db)
        logger.info(f"Trend explorer metrics for topic '{topic}':")
        logger.info(f"  Velocity: {res.data['velocity']}")
        logger.info(f"  Source Diversity: {res.data['source_diversity']} outlets")
        logger.info(f"  Freshness: {res.data['freshness']}")
        logger.info(f"  Covering Articles Count: {len(res.data['articles'])}")


async def verify_admin_controls():
    logger.info("\n--- 4. Verifying Administrative Controls Registry ---")
    async with AsyncSessionLocal() as db:
        res = await list_admin_sources(db=db)
        logger.info(f"Admin Registry Sources Count: {len(res.data)}")
        if res.data:
            target_id = res.data[0]["id"]
            toggle_res = await toggle_admin_source(id=target_id, db=db)
            logger.info(f"  Toggled Source: '{toggle_res.data['name']}' -> Enabled: {toggle_res.data['enabled']}")
            # Toggle it back to restore baseline state
            await toggle_admin_source(id=target_id, db=db)
            logger.info("  Restored source baseline enabled state.")


async def main():
    logger.info("========================================================")
    logger.info("STARTING PHASE 3 EDITORIAL UX VERIFICATION")
    logger.info("========================================================")
    try:
        await verify_search_filters()
        await verify_telemetry_sources()
        await verify_trend_explorer()
        await verify_admin_controls()
        logger.info("\n========================================================")
        logger.info("VERIFICATION COMPLETE: ALL PHASE 3 BACKEND APIS FUNCTIONAL")
        logger.info("========================================================")
    except Exception as e:
        logger.error(f"Verification Failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
