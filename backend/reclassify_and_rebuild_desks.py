"""
Operational Activation: Stage 4
===============================
Reclassifies all database articles using the new classification contract,
syncs PostgreSQL categories, rebuilds category desk projections,
and invalidates Redis cache.
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import select, update, cast, String
from app.core.database import AsyncSessionLocal
from app.models.article import Category, ProcessedArticle, ArticleReadModel
from app.editorial.homepage_builder import HomepageBuilder
from app.services.ingestion.processor import map_category_slug, map_category_id
from app.core.redis import redis_client

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("stage4_activation")

TAXONOMY = [
    {"slug": "artificial-intelligence", "name": "Artificial Intelligence"},
    {"slug": "cybersecurity", "name": "Cybersecurity"},
    {"slug": "hardware", "name": "Hardware & Devices"},
    {"slug": "robotics", "name": "Robotics"},
    {"slug": "science", "name": "Science & Quantum"},
    {"slug": "startups-and-business", "name": "Startups & Business"},
    {"slug": "policy", "name": "Policy & Governance"},
    {"slug": "technology", "name": "General Technology"},
]

async def execute_stage_4():
    logger.info("Starting Stage 4 Operational Activation...")

    async with AsyncSessionLocal() as db:
        # Step 1: Sync/Seed Categories in PostgreSQL
        logger.info("Step 1: Syncing 8-category taxonomy in DB...")
        cat_map = {}
        for item in TAXONOMY:
            stmt = select(Category).where(Category.slug == item["slug"])
            res = await db.execute(stmt)
            cat = res.scalars().first()
            if not cat:
                cat = Category(slug=item["slug"], name=item["name"])
                db.add(cat)
                await db.flush()
                logger.info(f"  Created Category: {item['name']} (ID: {cat.id})")
            else:
                cat.name = item["name"]
                logger.info(f"  Existing Category: {item['name']} (ID: {cat.id})")
            cat_map[item["slug"]] = cat.id

        await db.commit()

        # Step 2: Reclassify ProcessedArticle and ArticleReadModel
        logger.info("Step 2: Reclassifying articles...")
        # Fetch ProcessedArticles and ArticleReadModel
        stmt = (
            select(ProcessedArticle, ArticleReadModel.source, ArticleReadModel.title)
            .join(ArticleReadModel, cast(ProcessedArticle.id, String) == ArticleReadModel.id)
        )
        res = await db.execute(stmt)
        rows = res.all()

        updated_count = 0
        cat_distribution = {}

        for proc_art, source_name, title in rows:
            new_slug = map_category_slug(title, proc_art.content or "", source_name)
            new_cat_id = cat_map.get(new_slug, cat_map["technology"])

            proc_art.category_id = new_cat_id
            
            # Also update ArticleReadModel category column (which stores category display name)
            cat_name = next(t["name"] for t in TAXONOMY if t["slug"] == new_slug)
            arm_stmt = (
                update(ArticleReadModel)
                .where(ArticleReadModel.id == str(proc_art.id))
                .values(category=cat_name)
            )
            await db.execute(arm_stmt)

            cat_distribution[new_slug] = cat_distribution.get(new_slug, 0) + 1
            updated_count += 1

        await db.commit()
        logger.info(f"  Successfully reclassified {updated_count} articles!")
        logger.info("  New Category Distribution:")
        for k, v in cat_distribution.items():
            logger.info(f"    - {k}: {v}")

        # Step 3: Rebuild CategoryDeskProjection
        logger.info("Step 3: Rebuilding CategoryDeskProjection...")
        await HomepageBuilder.build_and_persist_category_desks(db)

        # Step 4: Rebuild HomepageProjection
        logger.info("Step 4: Rebuilding HomepageProjection...")
        await HomepageBuilder.build_and_persist_homepage_projection(db)

        # Step 5: Flush / Invalidate Redis Caches
        logger.info("Step 5: Invalidating Redis cache...")
        if redis_client:
            try:
                # Delete desk keys and homepage projection keys
                keys = await redis_client.keys("*news*") + await redis_client.keys("*homepage*") + await redis_client.keys("*desk*")
                if keys:
                    await redis_client.delete(*keys)
                    logger.info(f"  Invalidated {len(keys)} Redis keys.")
            except Exception as e:
                logger.warning(f"  Failed to flush Redis keys: {e}")

        logger.info("Stage 4 Activation Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(execute_stage_4())
