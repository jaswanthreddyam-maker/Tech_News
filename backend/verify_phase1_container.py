import asyncio
import json
import os
import sys

sys.path.insert(0, os.getcwd())

import redis.asyncio as redis
from sqlalchemy import select
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.editorial.homepage_builder import HomepageBuilder
from app.models.article import ArticleReadModel
from app.models.projection import HomepageProjection
from app.models.source import Source
from app.services.cache_service import CacheService
from app.services.ingestion.pipeline import run_source_ingestion_pipeline

async def run_phase1_verification():
    print("==================================================================")
    print("EXECUTION CERTIFICATION: PHASE 1 ARCHITECTURE & VERIFICATION")
    print("==================================================================")

    # 1. Clear Redis Cache
    print("\n--- Step 1: Clearing Redis Cache ---")
    invalidated = await CacheService.invalidate_homepage_cache(reason="phase1_verification_init")
    print(f"Redis Cache Invalidated: {invalidated}")

    # 2. Rebuild HomepageProjection
    print("\n--- Step 2: Rebuilding HomepageProjection via HomepageBuilder ---")
    async with AsyncSessionLocal() as session:
        articles = await HomepageBuilder.build_and_persist_homepage_projection(session)
        await session.commit()
        print(f"HomepageBuilder generated {len(articles)} articles for projection.")
        for idx, a in enumerate(articles, 1):
            clean_t = str(a.title).encode('ascii', 'ignore').decode('ascii')
            print(f"  {idx}. ID: '{a.id}' | Source: [{a.source}] | Title: '{clean_t[:60]}...'")

    # 3. Validate CQRS Identity Invariant Match in Redis
    print("\n--- Step 3: Validating Redis <-> Projection CQRS Invariants ---")
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    cached = await r.get("editorial:v1:homepage_ranked_ids")
    if not cached:
        print("[FAIL] Redis key missing after HomepageBuilder rebuild!")
    else:
        cache_data = json.loads(cached)
        print("Redis Cached Payload:")
        print(f"  projection_id:      '{cache_data.get('projection_id')}'")
        print(f"  projection_version: {cache_data.get('projection_version')}")
        print(f"  algorithm_version:  '{cache_data.get('algorithm_version')}'")
        print(f"  article_ids count:  {len(cache_data.get('article_ids', []))}")

        async with AsyncSessionLocal() as session:
            hp_res = await session.execute(select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1))
            latest_hp = hp_res.scalars().first()
            if not latest_hp:
                print("[FAIL] No HomepageProjection found in DB!")
            else:
                inv_id = str(cache_data.get("projection_id")) == str(latest_hp.id)
                inv_ver = cache_data.get("projection_version") == latest_hp.projection_version
                inv_algo = cache_data.get("algorithm_version") == settings.EDITORIAL_ALGORITHM_VERSION
                
                # Check DB existence via single IN query
                str_ids = [str(aid) for aid in cache_data.get("article_ids", [])]
                db_ids_res = await session.execute(select(ArticleReadModel.id).where(ArticleReadModel.id.in_(str_ids)))
                db_ids = set(db_ids_res.scalars().all())
                inv_ids = db_ids == set(str_ids)

                print(f"  Invariant 1 (projection_id match):      {'[PASS]' if inv_id else '[FAIL]'}")
                print(f"  Invariant 2 (projection_version match): {'[PASS]' if inv_ver else '[FAIL]'}")
                print(f"  Invariant 3 (algorithm_version match):  {'[PASS]' if inv_algo else '[FAIL]'}")
                print(f"  Invariant 4 (single IN query match):    {'[PASS]' if inv_ids else '[FAIL]'}")

    # 4. Execute Ingestion Pipeline Run
    print("\n--- Step 4: Executing Ingestion Cycle across All Configured Sources ---")
    async with AsyncSessionLocal() as session:
        sources_res = await session.execute(select(Source).where(Source.enabled == True))
        sources = sources_res.scalars().all()
        # Reset last_crawl_at to force immediate crawl
        for s in sources:
            s.last_crawl_at = None
        await session.commit()

        metrics = await run_source_ingestion_pipeline(session)
        print(f"Ingestion Run Completed. Metrics: {metrics}")

    # 5. Audit Source Distribution & Telemetry Post-Ingestion
    print("\n--- Step 5: Post-Ingestion Source Distribution & Read Model Audit ---")
    async with AsyncSessionLocal() as session:
        arm_res = await session.execute(select(ArticleReadModel.source))
        all_sources = arm_res.scalars().all()
        print(f"Total Published Articles in ArticleReadModel: {len(all_sources)}")
        from collections import Counter
        counts = Counter(all_sources)
        for src, cnt in counts.most_common():
            pct = (cnt / len(all_sources)) * 100 if all_sources else 0
            print(f"  - {src}: {cnt} ({pct:.1f}%)")

    # 6. Verify API Response /api/v1/news
    print("\n--- Step 6: Querying API Endpoint /api/v1/news?sort_by=trending ---")
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:8000/api/v1/news?limit=12&sort_by=trending")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get("items", data.get("data", []))
            print(f"API Returned {len(items)} items:")
            api_sources = [item.get("source") for item in items]
            api_counts = Counter(api_sources)
            for src, cnt in api_counts.most_common():
                pct = (cnt / len(items)) * 100 if items else 0
                print(f"  - {src}: {cnt} ({pct:.1f}%)")
    except Exception as e:
        print(f"API Query Warning: {e}")

    await r.aclose()

if __name__ == "__main__":
    asyncio.run(run_phase1_verification())
