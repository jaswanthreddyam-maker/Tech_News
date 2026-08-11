
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import ArticleEntityLink, ArticleTopicLink, EntityNode
from app.schemas.news import ArticleCard
from app.schemas.responses import PaginatedResponse, PaginationMetadata

router = APIRouter()

from typing import Any
from fastapi import Response, Query, Depends

_in_memory_homepage_cache: dict[str, Any] = {
    "cards": None,
    "expires_at": 0.0
}

@router.get("", response_model=PaginatedResponse[ArticleCard])
async def list_articles(
    response: Response,
    category: str | None = Query(None, description="Topic filter slug"),
    cursor: str | None = Query(None, description="Cursor for pagination"),
    sort_by: str | None = Query(None, description="Sort ordering"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch articles from ArticleReadModel using the versioned Redis ranking cache.
    """
    import time
    t0 = time.time()
    now_ts = time.time()

    # Fast Path 0: Process-level in-memory cache (1ms response, completely immune to DB/Redis latency)
    if not category and not cursor and not sort_by and _in_memory_homepage_cache.get("cards") and now_ts < _in_memory_homepage_cache.get("expires_at", 0):
        cards_data = _in_memory_homepage_cache["cards"]
        t_total = time.time() - t0
        response.headers["Server-Timing"] = f"mem_hit;dur={t_total*1000:.1f}"
        return PaginatedResponse(
            correlation_id=correlation_id_ctx.get() or "system",
            data=cards_data[:limit],
            pagination=PaginationMetadata(next_cursor=None, has_more=False, limit=limit),
        )

    correlation_id = correlation_id_ctx.get() or "system"

    from app.core.redis import get_redis_client
    from app.core.config import settings
    from datetime import datetime, timezone, timedelta
    import json
    import logging

    logger = logging.getLogger("tech_news.routes.news")

    cached = None
    cache_key_full = "editorial:v2:homepage_cards_full_json"
    cache_key = "editorial:v2:homepage_ranked_ids"
    REDIS_OP_TIMEOUT = 1.0

    try:
        import asyncio
        redis = get_redis_client()
        if redis and not category and not cursor:
            cached_full = await asyncio.wait_for(redis.get(cache_key_full), timeout=REDIS_OP_TIMEOUT)
            if cached_full:
                cards_data = json.loads(cached_full)
                t_total = time.time() - t0
                response.headers["Server-Timing"] = f"redis_hit;dur={(time.time()-t0)*1000:.1f}"
                return PaginatedResponse(
                    correlation_id=correlation_id,
                    data=cards_data[:limit],
                    pagination=PaginationMetadata(next_cursor=None, has_more=False, limit=limit),
                )
            cached = await asyncio.wait_for(redis.get(cache_key), timeout=REDIS_OP_TIMEOUT)
    except Exception as e:
        from app.core.redis import mark_redis_failed
        mark_redis_failed()
        logger.warning(f"Redis cache read failed (proceeding without cache): {e}")
    t_redis = time.time() - t0

    ranked_ids = []
    cache_meta = {}
    if cached:
        try:
            cache_meta = json.loads(cached)
            ranked_ids = cache_meta.get("article_ids", [])
        except Exception:
            pass

    articles = []
    is_stale_state = False

    # Path 1: Check Redis ranking cache & CQRS Identity Invariants
    if ranked_ids:
        algo_ver = cache_meta.get("algorithm_version")
        expected_algo = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v1")
        
        # Invariant 1: Algorithm version match
        if algo_ver != expected_algo:
            logger.info(f"Redis cache algorithm version mismatch (cached: {algo_ver}, expected: {expected_algo}). Invalidating.")
            is_stale_state = True
        else:
            # Invariant 2: Compare projection_id & projection_version against DB HomepageProjection
            try:
                from app.models.projection import HomepageProjection
                proj_stmt = select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1)
                proj_res = await db.execute(proj_stmt)
                latest_projection = proj_res.scalars().first()

                if not latest_projection:
                    is_stale_state = True
                else:
                    cached_proj_id = str(cache_meta.get("projection_id", ""))
                    cached_proj_ver = cache_meta.get("projection_version")
                    if cached_proj_id != str(latest_projection.id) or cached_proj_ver != latest_projection.projection_version:
                        logger.info(f"Redis cache projection identity mismatch (cached v{cached_proj_ver}, DB v{latest_projection.projection_version}). Invalidating.")
                        is_stale_state = True
            except Exception as e:
                logger.warning(f"HomepageProjection query failed: {e}. Falling back to rebuild.")
                is_stale_state = True

        if not is_stale_state:
            # Invariant 3: Single SQL IN query to resolve all IDs at once (Guardrail #3)
            str_ranked_ids = [str(aid) for aid in ranked_ids]
            if str_ranked_ids:
                stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(str_ranked_ids))
                res = await db.execute(stmt)
                articles_map = {str(art.id): art for art in res.scalars().all()}
                
                if set(articles_map.keys()) != set(str_ranked_ids):
                    logger.warning(f"Partial ID resolution in Redis cache: requested {len(str_ranked_ids)}, found {len(articles_map)}. Invalidating.")
                    is_stale_state = True
                else:
                    articles = [articles_map[aid] for aid in str_ranked_ids if aid in articles_map]
            else:
                is_stale_state = True

    # Path 2: Check latest HomepageProjection CQRS read model
    if not articles and not is_stale_state:
        try:
            from app.models.projection import HomepageProjection
            proj_stmt = select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1)
            proj_res = await db.execute(proj_stmt)
            latest_projection = proj_res.scalars().first()

            if latest_projection and latest_projection.stories_json:
                story_ids = [str(s["id"]) for s in latest_projection.stories_json if "id" in s]
                if story_ids:
                    stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(story_ids))
                    res = await db.execute(stmt)
                    articles_map = {str(art.id): art for art in res.scalars().all()}
                    
                    if set(articles_map.keys()) != set(story_ids):
                        logger.warning(f"Partial resolution in HomepageProjection v{latest_projection.projection_version}: requested {len(story_ids)}, resolved {len(articles_map)}. Triggering rebuild.")
                        is_stale_state = True
                    else:
                        articles = [articles_map[aid] for aid in story_ids if aid in articles_map]
                        ranked_ids = [str(a.id) for a in articles]
                        try:
                            import asyncio
                            algo_ver = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v1")
                            cache_payload = {
                                "projection_id": str(latest_projection.id),
                                "projection_version": latest_projection.projection_version,
                                "algorithm_version": algo_ver,
                                "generated_at": datetime.now(timezone.utc).isoformat(),
                                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                                "article_ids": ranked_ids
                            }
                            redis = get_redis_client()
                            if redis:
                                await asyncio.wait_for(redis.set(cache_key, json.dumps(cache_payload), ex=3600), timeout=REDIS_OP_TIMEOUT)
                        except Exception as e:
                            logger.warning(f"Redis cache write failed: {e}")
        except Exception as e:
            logger.warning(f"HomepageProjection Path 2 read failed: {e}. Falling back to rebuild.")

    # Path 3: Concurrent-safe rebuild using RedisDistributedLock with safe fallback path (Guardrail #3)
    if not articles or is_stale_state:
        from app.core.redis import RedisDistributedLock
        from app.editorial.homepage_builder import HomepageBuilder
        from app.services.cache_service import CacheService

        lock = RedisDistributedLock("homepage_projection_rebuild", expire_seconds=30)
        lock_acquired = False
        try:
            async with lock:
                lock_acquired = True
                # Double-check: another concurrent request may have repaired the projection while waiting for lock
                rechecked_articles = []
                try:
                    redis = get_redis_client()
                    if redis:
                        fresh_cached = await asyncio.wait_for(redis.get(cache_key), timeout=REDIS_OP_TIMEOUT)
                        if fresh_cached:
                            fresh_data = json.loads(fresh_cached)
                            fresh_ids = [str(aid) for aid in fresh_data.get("article_ids", [])]
                            if fresh_ids:
                                f_stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(fresh_ids))
                                f_res = await db.execute(f_stmt)
                                f_map = {str(art.id): art for art in f_res.scalars().all()}
                                if set(f_map.keys()) == set(fresh_ids):
                                    rechecked_articles = [f_map[aid] for aid in fresh_ids if aid in f_map]
                except Exception as e:
                    logger.warning(f"Double-check Redis read failed: {e}")

                if rechecked_articles:
                    articles = rechecked_articles
                    logger.info("Double-check succeeded: HomepageProjection was repaired by a concurrent worker.")
                else:
                    logger.info("Acquired homepage rebuild lock. Executing canonical homepage projection rebuild.")
                    await CacheService.invalidate_homepage_cache(reason="projection_rebuild")
                    global_articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
                    articles = global_articles
                    ranked_ids = [str(a.id) for a in global_articles]

                    # Fetch the newly created projection metadata
                    from app.models.projection import HomepageProjection
                    new_proj_res = await db.execute(select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1))
                    new_proj = new_proj_res.scalars().first()

                    try:
                        import asyncio
                        algo_ver = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v1")
                        cache_payload = {
                            "projection_id": str(new_proj.id) if new_proj else "",
                            "projection_version": new_proj.projection_version if new_proj else 1,
                            "algorithm_version": algo_ver,
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                            "article_ids": ranked_ids
                        }
                        redis = get_redis_client()
                        if redis:
                            await asyncio.wait_for(redis.set(cache_key, json.dumps(cache_payload), ex=3600), timeout=REDIS_OP_TIMEOUT)
                    except Exception as e:
                        logger.warning(f"Redis cache write failed: {e}")
        except Exception as lock_err:
            logger.warning(f"Could not acquire rebuild lock (or lock failed): {lock_err}. Falling back to DB read model.")
            # Guardrail #3 Safe Fallback Path: Do NOT bypass lock to execute parallel rebuild. Read latest DB projection.
            from app.models.projection import HomepageProjection
            fallback_proj = (await db.execute(select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1))).scalars().first()
            if fallback_proj and fallback_proj.stories_json:
                fb_ids = [str(s["id"]) for s in fallback_proj.stories_json if "id" in s]
                fb_res = await db.execute(select(ArticleReadModel).where(ArticleReadModel.id.in_(fb_ids)))
                fb_map = {str(a.id): a for a in fb_res.scalars().all()}
                articles = [fb_map[aid] for aid in fb_ids if aid in fb_map]



    # If category filter is active, filter from the global ranked articles
    if category:
        category_lower = category.lower().strip()
        filtered_articles = []
        for art in articles:
            topic_stmt = select(ArticleTopicLink.topic_name).where(ArticleTopicLink.article_id == art.id)
            topic_res = await db.execute(topic_stmt)
            topics = topic_res.scalars().all()
            if any(category_lower in t.lower() for t in topics):
                filtered_articles.append(art)
        articles = filtered_articles

    # Paginate by slicing
    articles = articles[:limit]

    # Batch fetch topics and entities for all articles in 2 single queries (eliminates N+1 loop delay)
    art_ids = [art.id for art in articles]
    topics_by_art: dict[str, list[str]] = {}
    entities_by_art: dict[str, list[str]] = {}

    if art_ids:
        from app.models.tnt_knowledge import ArticleEntityLink, EntityNode
        # 1. Batch topics
        t_stmt = select(ArticleTopicLink.article_id, ArticleTopicLink.topic_name).where(ArticleTopicLink.article_id.in_(art_ids))
        t_res = await db.execute(t_stmt)
        for row in t_res.all():
            topics_by_art.setdefault(str(row[0]), []).append(row[1])

        # 2. Batch entities
        e_stmt = select(ArticleEntityLink.article_id, EntityNode.canonical_name).join(
            EntityNode, EntityNode.id == ArticleEntityLink.entity_id
        ).where(ArticleEntityLink.article_id.in_(art_ids))
        e_res = await db.execute(e_stmt)
        for row in e_res.all():
            art_id_str = str(row[0])
            if len(entities_by_art.get(art_id_str, [])) < 3:
                entities_by_art.setdefault(art_id_str, []).append(row[1])

    articles_list = []
    for art in articles:
        topics = topics_by_art.get(str(art.id), [])
        entities = entities_by_art.get(str(art.id), [])
        card = ArticleCard.from_model(
            art,
            topics=topics,
            entities=entities
        )
        articles_list.append(card)

    if not category and not cursor and articles_list:
        raw_cards = [c.model_dump(mode="json") if hasattr(c, "model_dump") else c.dict() for c in articles_list]
        _in_memory_homepage_cache["cards"] = raw_cards
        _in_memory_homepage_cache["expires_at"] = time.time() + 60.0
        try:
            redis = get_redis_client()
            if redis:
                await asyncio.wait_for(redis.set(cache_key_full, json.dumps(raw_cards, default=str), ex=300), timeout=REDIS_OP_TIMEOUT)
        except Exception as cache_err:
            logger.warning(f"Failed to cache full payload: {cache_err}")

    t_total = time.time() - t0
    response.headers["Server-Timing"] = f"redis;dur={t_redis*1000:.1f}, total;dur={t_total*1000:.1f}"

    return PaginatedResponse(
        correlation_id=correlation_id,
        data=articles_list,
        pagination=PaginationMetadata(next_cursor=None, has_more=False, limit=limit),
    )

@router.get("/purge-cache")
@router.post("/purge-cache")
async def purge_news_cache(db: AsyncSession = Depends(get_db)):
    """
    Clears stale Redis homepage cache and forces a fresh projection rebuild.
    """
    from app.core.redis import get_redis_client
    from app.editorial.homepage_builder import HomepageBuilder
    from app.models.projection import HomepageProjection, CategoryDeskProjection
    from sqlalchemy import delete

    _in_memory_homepage_cache["cards"] = None
    _in_memory_homepage_cache["expires_at"] = 0.0

    await db.execute(delete(HomepageProjection))
    await db.execute(delete(CategoryDeskProjection))
    await db.commit()

    try:
        redis = get_redis_client()
        if redis:
            keys = await redis.keys("editorial:*")
            if keys:
                await redis.delete(*keys)
    except Exception:
        pass

    articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
    await HomepageBuilder.build_and_persist_category_desks(db)
    return {"status": "success", "message": f"Cache purged. Homepage rebuilt with {len(articles)} articles and category desks updated."}


import html
from datetime import datetime, timezone

from fastapi import Response


@router.get("/rss.xml")
async def get_rss(db: AsyncSession = Depends(get_db)):
    """
    Generate an RSS 2.0 feed from the canonical ArticleReadModel.
    """
    stmt = select(ArticleReadModel).where(ArticleReadModel.is_test_data == False).order_by(desc(ArticleReadModel.published_at)).limit(20)
    result = await db.execute(stmt)
    articles = result.scalars().all()

    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

    items = []
    for art in articles:
        link = art.url or f"https://technewstoday.com/articles/{art.id}"
        desc_escaped = html.escape(art.summary or "")
        title_escaped = html.escape(art.title or "")
        art_pub = art.published_at.strftime("%a, %d %b %Y %H:%M:%S %z") if art.published_at else pub_date

        item = f"""
        <item>
            <title>{title_escaped}</title>
            <link>{link}</link>
            <description>{desc_escaped}</description>
            <pubDate>{art_pub}</pubDate>
            <guid>{link}</guid>
        </item>
        """
        items.append(item)

    items_xml = "".join(items)

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>Tech News Today</title>
    <link>https://technewstoday.com</link>
    <description>The latest technology news, powered by AI.</description>
    <language>en-us</language>
    <pubDate>{pub_date}</pubDate>
    <lastBuildDate>{pub_date}</lastBuildDate>
    {items_xml}
</channel>
</rss>
"""
    return Response(content=rss_xml.strip(), media_type="application/xml")

@router.get("/desks")
async def get_category_desks(db: AsyncSession = Depends(get_db)):
    """
    Returns the aggregated Category Desk projection joined with runtime configuration.
    """
    from app.models.projection import CategoryDeskProjection
    from app.models.article import ArticleReadModel
    from pathlib import Path
    import yaml

    # 1. Load configuration
    policy_path = Path("app/editorial/category_policy.yaml")
    policy_data = {}
    if policy_path.exists():
        with open(policy_path, "r") as f:
            policy_data = yaml.safe_load(f) or {}
    
    categories_cfg = policy_data.get("categories", {})

    # 2. Query all projections
    stmt = select(CategoryDeskProjection)
    res = await db.execute(stmt)
    projections = res.scalars().all()

    # Auto-heal: rebuild if projections don't exist or contain no valid articles
    has_valid_articles = any(p.article_ids for p in projections if p.article_ids)
    if not projections or not has_valid_articles:
        from app.editorial.homepage_builder import HomepageBuilder
        await HomepageBuilder.build_and_persist_category_desks(db)
        stmt = select(CategoryDeskProjection)
        res = await db.execute(stmt)
        projections = res.scalars().all()

    # 3. Collect all article IDs needed
    all_article_ids = set()
    for p in projections:
        if p.article_ids:
            all_article_ids.update(p.article_ids)
    
    articles_map = {}
    if all_article_ids:
        from sqlalchemy.orm import defer
        art_stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(all_article_ids)).options(
            defer(ArticleReadModel.content),
            defer(ArticleReadModel.embedding)
        )
        art_res = await db.execute(art_stmt)
        # Convert objects to dicts so they serialize nicely
        for a in art_res.scalars().all():
            adict = {k: v for k, v in a.__dict__.items() if not k.startswith("_")}
            articles_map[str(a.id)] = adict
    
    desks = []
    for p in projections:
        slug = p.category_slug
        if slug not in categories_cfg:
            continue
            
        cfg = categories_cfg[slug]
        headline = cfg.get("headline", slug.capitalize())
        display_order = cfg.get("display_order", 999)
        
        desk_articles = []
        for aid in p.article_ids or []:
            if aid in articles_map:
                desk_articles.append(articles_map[aid])
                
        desks.append({
            "slug": slug,
            "headline": headline,
            "display_order": display_order,
            "articles": desk_articles
        })
        
    desks.sort(key=lambda x: x["display_order"])
    return desks

