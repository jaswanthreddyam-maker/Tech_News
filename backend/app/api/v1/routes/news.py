
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, or_, select
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

from app.services.cache_service import in_memory_homepage_cache as _in_memory_homepage_cache

@router.get("", response_model=PaginatedResponse[ArticleCard])
async def list_articles(
    response: Response,
    category: str | None = Query(None, description="Topic filter slug"),
    cursor: str | None = Query(None, description="Cursor for pagination"),
    sort_by: str | None = Query(None, description="Sort ordering"),
    limit: int = Query(10, ge=1, le=100),
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

    import asyncio
    import json
    import logging
    from app.core.database import AsyncSessionLocal
    from app.core.redis import get_redis_client
    from app.core.config import settings
    from app.models.article import ProcessedArticle
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import cast, String, func, and_, or_

    logger = logging.getLogger("tech_news.routes.news")

    t_redis = 0.0
    cache_key_full = "editorial:v2:homepage_cards_full_json"
    cache_key = "editorial:v2:homepage_ranked_ids"
    REDIS_OP_TIMEOUT = 1.0

    now_utc = datetime.now(timezone.utc)
    cutoff_hours = getattr(settings, "EDITORIAL_WINDOW_HOURS", 24)
    cutoff = now_utc - timedelta(hours=cutoff_hours)

    # ── Special Path: sort_by == "freshness" (Breaking News Feed) ──
    if sort_by == "freshness":
        cache_key_fresh = f"editorial:v2:freshness_cards_json:{limit}"
        try:
            redis = get_redis_client()
            if redis and not category and not cursor:
                cached_fresh = await asyncio.wait_for(redis.get(cache_key_fresh), timeout=REDIS_OP_TIMEOUT)
                if cached_fresh:
                    fresh_cards_data = json.loads(cached_fresh)
                    response.headers["Server-Timing"] = f"redis_hit;dur={(time.time()-t0)*1000:.1f}"
                    return PaginatedResponse(
                        correlation_id=correlation_id,
                        data=fresh_cards_data[:limit],
                        pagination=PaginationMetadata(next_cursor=None, has_more=False, limit=limit),
                    )
        except Exception:
            pass

        async def fetch_fresh_data(db):
            from sqlalchemy.orm import defer
            stmt_fresh = (
                select(ArticleReadModel)
                .where(
                    ArticleReadModel.is_test_data == False,
                    ArticleReadModel.publication_status == "PUBLISHED",
                )
                .order_by(desc(ArticleReadModel.published_at))
                .limit(limit)
                .options(defer(ArticleReadModel.content), defer(ArticleReadModel.embedding))
            )
            res_fresh = await db.execute(stmt_fresh)
            fresh_articles = res_fresh.scalars().all()

            art_ids = [art.id for art in fresh_articles]
            topics_by_art: dict[str, list[str]] = {}
            entities_by_art: dict[str, list[str]] = {}

            if art_ids:
                from app.models.tnt_knowledge import ArticleEntityLink, EntityNode
                try:
                    t_stmt = select(ArticleTopicLink.article_id, ArticleTopicLink.topic_name).where(ArticleTopicLink.article_id.in_(art_ids))
                    t_res = await db.execute(t_stmt)
                    for row in t_res.all():
                        topics_by_art.setdefault(str(row[0]), []).append(row[1])

                    e_stmt = select(ArticleEntityLink.article_id, EntityNode.canonical_name).join(
                        EntityNode, EntityNode.id == ArticleEntityLink.entity_id
                    ).where(ArticleEntityLink.article_id.in_(art_ids))
                    e_res = await db.execute(e_stmt)
                    for row in e_res.all():
                        art_id_str = str(row[0])
                        if len(entities_by_art.get(art_id_str, [])) < 3:
                            entities_by_art.setdefault(art_id_str, []).append(row[1])
                except Exception as meta_err:
                    logger.warning(f"Error loading topic/entity metadata for fresh articles: {meta_err}")

            return [
                ArticleCard.from_model(
                    art,
                    topics=topics_by_art.get(str(art.id), []),
                    entities=entities_by_art.get(str(art.id), [])
                ) for art in fresh_articles
            ]

        try:
            from app.core.database import safe_db_execute
            articles_list = await safe_db_execute(fetch_fresh_data, fallback=[])

            # Cache in Redis with 60s TTL
            try:
                redis = get_redis_client()
                if redis and articles_list and not category and not cursor:
                    raw_cards = [c.model_dump(mode="json") if hasattr(c, "model_dump") else c.dict() for c in articles_list]
                    await asyncio.wait_for(redis.set(cache_key_fresh, json.dumps(raw_cards, default=str), ex=180), timeout=REDIS_OP_TIMEOUT)
            except Exception:
                pass

            response.headers["Server-Timing"] = f"db;dur={(time.time()-t0)*1000:.1f}"
            return PaginatedResponse(
                correlation_id=correlation_id,
                data=articles_list,
                pagination=PaginationMetadata(next_cursor=None, has_more=False, limit=limit),
            )
        except Exception as e:
            logger.error(f"Error querying fresh articles feed: {e}", exc_info=True)
            return PaginatedResponse(
                correlation_id=correlation_id,
                data=[],
                pagination=PaginationMetadata(next_cursor=None, has_more=False, limit=limit),
            )
    else:
        cached = None

        try:
            redis = get_redis_client()
            if redis and not category and not cursor:
                cached_full = await asyncio.wait_for(redis.get(cache_key_full), timeout=REDIS_OP_TIMEOUT)
                if cached_full:
                    cards_data = json.loads(cached_full)
                    # Verify cards in cached payload are not expired
                    cached_dates = [c.get("published_at") for c in cards_data if isinstance(c, dict)]
                    all_fresh = True
                    for dt_str in cached_dates:
                        if dt_str:
                            try:
                                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                                if dt < cutoff - timedelta(hours=24):  # older than 48h
                                    all_fresh = False
                                    break
                            except Exception:
                                pass
                    if all_fresh:
                        t_total = time.time() - t0
                        response.headers["Server-Timing"] = f"redis_hit;dur={(time.time()-t0)*1000:.1f}"
                        return PaginatedResponse(
                            correlation_id=correlation_id,
                            data=cards_data[:limit],
                            pagination=PaginationMetadata(next_cursor=None, has_more=False, limit=limit),
                        )
                    else:
                        logger.info("Cached Redis cards contain stale/expired articles. Invalidating.")
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

        async def fetch_homepage_articles(db):
            nonlocal ranked_ids, is_stale_state
            resolved_articles = []

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
                            else:
                                # Invariant 2b: Check if projection is older than 24 hours
                                proj_created = latest_projection.created_at
                                if proj_created.tzinfo is None:
                                    proj_created = proj_created.replace(tzinfo=timezone.utc)
                                if (now_utc - proj_created).total_seconds() > 86400:
                                    logger.info("DB HomepageProjection is older than 24 hours. Marking stale.")
                                    is_stale_state = True
                    except Exception as e:
                        logger.warning(f"HomepageProjection query failed: {e}. Falling back to rebuild.")
                        is_stale_state = True

                if not is_stale_state:
                    # Invariant 3: Single SQL IN query to resolve all IDs at once & verify non-expired
                    str_ranked_ids = [str(aid) for aid in ranked_ids]
                    int_ranked_ids = [int(aid) for aid in ranked_ids if str(aid).isdigit()]
                    
                    if str_ranked_ids:
                        # Check if any ranked IDs are marked expired in ProcessedArticle
                        if int_ranked_ids:
                            exp_cnt_stmt = select(func.count(ProcessedArticle.id)).where(
                                ProcessedArticle.id.in_(int_ranked_ids),
                                or_(
                                    ProcessedArticle.is_expired == True,
                                    ProcessedArticle.is_archived == True,
                                    and_(ProcessedArticle.expires_at != None, ProcessedArticle.expires_at <= now_utc),
                                ),
                            )
                            exp_cnt = (await db.execute(exp_cnt_stmt)).scalar() or 0
                            if exp_cnt > 0:
                                logger.info(f"Redis cache contains {exp_cnt} expired articles. Invalidating.")
                                is_stale_state = True

                        if not is_stale_state:
                            stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(str_ranked_ids))
                            res = await db.execute(stmt)
                            articles_map = {str(art.id): art for art in res.scalars().all()}
                            
                            if set(articles_map.keys()) != set(str_ranked_ids):
                                logger.warning(f"Partial ID resolution in Redis cache: requested {len(str_ranked_ids)}, found {len(articles_map)}. Invalidating.")
                                is_stale_state = True
                            else:
                                resolved_articles = [articles_map[aid] for aid in str_ranked_ids if aid in articles_map]
                    else:
                        is_stale_state = True

            # Path 2: Check latest HomepageProjection CQRS read model
            if not resolved_articles and not is_stale_state:
                try:
                    from app.models.projection import HomepageProjection
                    proj_stmt = select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1)
                    proj_res = await db.execute(proj_stmt)
                    latest_projection = proj_res.scalars().first()

                    if latest_projection and latest_projection.stories_json:
                        # Check projection age
                        proj_created = latest_projection.created_at
                        if proj_created.tzinfo is None:
                            proj_created = proj_created.replace(tzinfo=timezone.utc)
                        if (now_utc - proj_created).total_seconds() > 86400:
                            logger.info("DB HomepageProjection is older than 24 hours. Triggering rebuild.")
                            is_stale_state = True

                        story_ids = [str(s["id"]) for s in latest_projection.stories_json if "id" in s]
                        int_story_ids = [int(sid) for sid in story_ids if sid.isdigit()]
                        
                        # Verify none of the stories in projection are expired in ProcessedArticle
                        if not is_stale_state and int_story_ids:
                            exp_cnt_stmt = select(func.count(ProcessedArticle.id)).where(
                                ProcessedArticle.id.in_(int_story_ids),
                                or_(
                                    ProcessedArticle.is_expired == True,
                                    ProcessedArticle.is_archived == True,
                                    and_(ProcessedArticle.expires_at != None, ProcessedArticle.expires_at <= now_utc),
                                ),
                            )
                            exp_cnt = (await db.execute(exp_cnt_stmt)).scalar() or 0
                            if exp_cnt > 0:
                                logger.info(f"HomepageProjection contains {exp_cnt} expired articles. Triggering rebuild.")
                                is_stale_state = True

                        if not is_stale_state and story_ids:
                            stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(story_ids))
                            res = await db.execute(stmt)
                            articles_map = {str(art.id): art for art in res.scalars().all()}
                            
                            if set(articles_map.keys()) != set(story_ids):
                                logger.warning(f"Partial resolution in HomepageProjection v{latest_projection.projection_version}: requested {len(story_ids)}, resolved {len(articles_map)}. Triggering rebuild.")
                                is_stale_state = True
                            else:
                                resolved_articles = [articles_map[aid] for aid in story_ids if aid in articles_map]
                                ranked_ids = [str(a.id) for a in resolved_articles]
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
            if not resolved_articles or is_stale_state:
                from app.core.redis import RedisDistributedLock
                from app.editorial.homepage_builder import HomepageBuilder
                from app.services.cache_service import CacheService
                from app.services.ranking.news_ranking_engine import expire_articles

                lock = RedisDistributedLock("homepage_projection_rebuild", expire_seconds=30)
                try:
                    async with lock:
                        logger.info("Acquired homepage rebuild lock. Executing canonical expiration and homepage projection rebuild.")
                        await CacheService.invalidate_homepage_cache(reason="projection_rebuild")
                        await expire_articles(db)
                        global_articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
                        await HomepageBuilder.build_and_persist_category_desks(db)
                        resolved_articles = global_articles
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
                    from app.editorial.homepage_builder import HomepageBuilder
                    resolved_articles = await HomepageBuilder.build_homepage(db)

            # If category filter is active, filter from the global ranked articles
            if category:
                category_lower = category.lower().strip()
                filtered_articles = []
                for art in resolved_articles:
                    topic_stmt = select(ArticleTopicLink.topic_name).where(ArticleTopicLink.article_id == art.id)
                    topic_res = await db.execute(topic_stmt)
                    topics = topic_res.scalars().all()
                    if any(category_lower in t.lower() for t in topics):
                        filtered_articles.append(art)
                resolved_articles = filtered_articles

            # Paginate by slicing
            resolved_articles = resolved_articles[:limit]

            # Batch fetch topics and entities for all articles in 2 single queries (eliminates N+1 loop delay)
            art_ids = [art.id for art in resolved_articles]
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

            return [
                ArticleCard.from_model(
                    art,
                    topics=topics_by_art.get(str(art.id), []),
                    entities=entities_by_art.get(str(art.id), [])
                ) for art in resolved_articles
            ]

        try:
            from app.core.database import safe_db_execute
            articles_list = await safe_db_execute(fetch_homepage_articles, fallback=[])
        except Exception as exc:
            logger.error(f"Error fetching homepage articles: {exc}", exc_info=True)
            articles_list = []

    if not category and not cursor and articles_list:
        raw_cards = [c.model_dump(mode="json") if hasattr(c, "model_dump") else c.dict() for c in articles_list]
        if sort_by == "freshness":
            try:
                redis = get_redis_client()
                if redis:
                    cache_key_fresh = f"editorial:v2:freshness_cards_json:{limit}"
                    await asyncio.wait_for(redis.set(cache_key_fresh, json.dumps(raw_cards, default=str), ex=60), timeout=REDIS_OP_TIMEOUT)
            except Exception as cache_err:
                logger.warning(f"Failed to cache freshness payload: {cache_err}")
        else:
            _in_memory_homepage_cache["cards"] = raw_cards
            _in_memory_homepage_cache["expires_at"] = time.time() + 60.0
            try:
                redis = get_redis_client()
                if redis:
                    await asyncio.wait_for(redis.set(cache_key_full, json.dumps(raw_cards, default=str), ex=300), timeout=REDIS_OP_TIMEOUT)
            except Exception as cache_err:
                logger.warning(f"Failed to cache full payload: {cache_err}")

    t_total = time.time() - t0
    timing_parts = []
    if t_redis > 0:
        timing_parts.append(f"redis;dur={t_redis*1000:.1f}")
    timing_parts.append(f"total;dur={t_total*1000:.1f}")
    response.headers["Server-Timing"] = ", ".join(timing_parts)

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
    except Exception as e:
        logger.warning(f"Redis purge failed: {e}")

    articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
    await HomepageBuilder.build_and_persist_category_desks(db)
    return {"status": "success", "message": "News cache purged successfully"}


@router.get("/rss")
async def get_rss_feed(db: AsyncSession = Depends(get_db)):
    """
    Generates standard RSS 2.0 feed of the latest published tech news articles.
    """
    from app.models.article import ArticleReadModel
    from datetime import datetime, timezone
    import html

    stmt = select(ArticleReadModel).where(
        ArticleReadModel.is_test_data == False,
        ArticleReadModel.publication_status == "PUBLISHED"
    ).order_by(desc(ArticleReadModel.published_at)).limit(30)
    res = await db.execute(stmt)
    articles = res.scalars().all()

    now_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items_xml = []
    for a in articles:
        pub_date = a.published_at.strftime("%a, %d %b %Y %H:%M:%S +0000") if a.published_at else now_str
        title = html.escape(a.title or "Untitled")
        summary = html.escape(a.summary or "")
        link = f"https://technews.today/article/{a.slug or a.id}"
        items_xml.append(f"""
        <item>
            <title>{title}</title>
            <link>{link}</link>
            <description>{summary}</description>
            <pubDate>{pub_date}</pubDate>
            <guid isPermaLink="false">{a.id}</guid>
        </item>
        """)

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>Tech News Today | Autonomous AI Newsroom</title>
    <link>https://technews.today</link>
    <description>The latest verified breaking technology, AI, and cybersecurity news.</description>
    <lastBuildDate>{now_str}</lastBuildDate>
    <language>en-us</language>
    {"".join(items_xml)}
</channel>
</rss>
"""
    return Response(content=rss_xml.strip(), media_type="application/xml")

@router.get("/desks")
async def get_category_desks():
    """
    Returns the aggregated Category Desk projection joined with runtime configuration.
    Guarantees that expired articles are never included in desk feeds.
    Cached in Redis to protect database connection pools.
    """
    import asyncio
    import json
    import logging
    from app.core.redis import get_redis_client
    from app.schemas.article import ArticleCard
    from app.models.tnt_knowledge import ArticleTopicLink, ArticleEntityLink, EntityNode

    cache_key_desks = "editorial:v2:category_desks_json"
    try:
        redis = get_redis_client()
        if redis:
            cached_desks = await asyncio.wait_for(redis.get(cache_key_desks), timeout=1.0)
            if cached_desks:
                return json.loads(cached_desks)
    except Exception:
        pass

    from app.core.database import safe_db_execute
    from app.models.projection import CategoryDeskProjection
    from app.models.article import ArticleReadModel, ProcessedArticle
    from pathlib import Path
    from datetime import datetime, timezone
    from sqlalchemy import cast, String, func, or_
    import yaml

    now_utc = datetime.now(timezone.utc)
    logger = logging.getLogger("tech_news.routes.news")

    async def fetch_category_desks(db):
        # 1. Load configuration
        policy_path = Path(__file__).resolve().parents[3] / "editorial" / "category_policy.yaml"
        policy_data = {}
        if policy_path.exists():
            with open(policy_path, "r", encoding="utf-8") as f:
                policy_data = yaml.safe_load(f) or {}
        
        categories_cfg = policy_data.get("categories", {})

        # 2. Query all projections
        stmt = select(CategoryDeskProjection)
        res = await db.execute(stmt)
        projections = res.scalars().all()

        # Auto-heal: rebuild ONLY if projections don't exist at all
        if not projections or not any(p.article_ids for p in projections if p.article_ids):
            from app.core.redis import RedisDistributedLock
            from app.editorial.homepage_builder import HomepageBuilder
            lock = RedisDistributedLock("category_desks_rebuild", expire_seconds=30)
            try:
                async with lock:
                    await HomepageBuilder.build_and_persist_category_desks(db)
            except Exception as lock_err:
                logger.warning(f"Could not acquire category desks rebuild lock: {lock_err}")
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
            art_stmt = (
                select(ArticleReadModel)
                .outerjoin(ProcessedArticle, cast(ProcessedArticle.id, String) == ArticleReadModel.id)
                .where(
                    ArticleReadModel.id.in_(all_article_ids),
                    ArticleReadModel.is_test_data == False,
                    ArticleReadModel.publication_status == "PUBLISHED",
                    or_(ProcessedArticle.is_archived == None, ProcessedArticle.is_archived == False),
                    or_(ProcessedArticle.is_expired == None, ProcessedArticle.is_expired == False),
                    or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now_utc),
                )
                .options(defer(ArticleReadModel.content), defer(ArticleReadModel.embedding))
            )
            res = await db.execute(art_stmt)
            articles_map = {str(a.id): a for a in res.scalars().all()}

        # 4. Fetch topics and entities in bulk
        topics_by_art: dict[str, list[str]] = {}
        entities_by_art: dict[str, list[str]] = {}
        if all_article_ids:
            try:
                t_stmt = select(ArticleTopicLink.article_id, ArticleTopicLink.topic_name).where(ArticleTopicLink.article_id.in_(all_article_ids))
                t_res = await db.execute(t_stmt)
                for row in t_res.all():
                    topics_by_art.setdefault(str(row[0]), []).append(row[1])

                e_stmt = select(ArticleEntityLink.article_id, EntityNode.canonical_name).join(
                    EntityNode, EntityNode.id == ArticleEntityLink.entity_id
                ).where(ArticleEntityLink.article_id.in_(all_article_ids))
                e_res = await db.execute(e_stmt)
                for row in e_res.all():
                    art_id_str = str(row[0])
                    if len(entities_by_art.get(art_id_str, [])) < 3:
                        entities_by_art.setdefault(art_id_str, []).append(row[1])
            except Exception as meta_err:
                logger.warning(f"Error loading topic/entity metadata for category desks: {meta_err}")

        desks = []
        for p in projections:
            slug = p.category_slug
            cfg = categories_cfg.get(slug, {})
            headline = cfg.get("headline", slug.replace("-", " ").title())
            display_order = cfg.get("display_order", 99)

            desk_articles = []
            if p.article_ids:
                for aid in p.article_ids:
                    art = articles_map.get(str(aid))
                    if art:
                        card = ArticleCard.from_model(
                            art,
                            topics=topics_by_art.get(str(art.id), []),
                            entities=entities_by_art.get(str(art.id), [])
                        )
                        desk_articles.append(card.model_dump(mode="json") if hasattr(card, "model_dump") else card.dict())

            if not desk_articles:
                continue

            desks.append({
                "slug": slug,
                "headline": headline,
                "display_order": display_order,
                "articles": desk_articles
            })

        desks.sort(key=lambda d: d["display_order"])
        return desks

    try:
        desks = await safe_db_execute(fetch_category_desks, fallback=[])

        try:
            redis = get_redis_client()
            if redis and desks:
                await asyncio.wait_for(redis.set(cache_key_desks, json.dumps(desks, default=str), ex=300), timeout=1.0)
        except Exception:
            pass

        return desks
    except Exception as e:
        logger.error(f"Error serving category desks: {e}", exc_info=True)
        return []


async def _backfill_missing_thumbnails(db: AsyncSession):
    """Backfills og:image thumbnails for unthumbnailed published articles."""
    from app.models.article import ArticleReadModel, ProcessedArticle
    from agents.ingestion.rss_agent import RSSIngestionAgent
    from sqlalchemy import or_

    agent = RSSIngestionAgent()

    stmt = select(ProcessedArticle).where(
        or_(ProcessedArticle.thumbnail_url == None, ProcessedArticle.thumbnail_url == "")
    ).limit(30)
    res = await db.execute(stmt)
    for p in res.scalars().all():
        target = getattr(p, "source_url", None)
        if target and (target.startswith("http://") or target.startswith("https://")):
            img = agent._fetch_og_image(target)
            if img:
                p.thumbnail_url = img
                r_stmt = select(ArticleReadModel).where(ArticleReadModel.id == str(p.id))
                r_res = await db.execute(r_stmt)
                r_art = r_res.scalars().first()
                if r_art:
                    r_art.thumbnail_url = img
                    r_art.images = [img]

    await db.commit()


@router.api_route("/rebuild", methods=["GET", "POST"])
async def trigger_editorial_rebuild(db: AsyncSession = Depends(get_db)):
    """
    Manually triggers article expiration, live auto-replenishment,
    projection reconstruction, and Redis cache invalidation.
    """
    from app.services.ranking.news_ranking_engine import expire_articles
    from app.editorial.homepage_builder import HomepageBuilder
    from app.services.cache_service import CacheService
    from app.services.ingestion.replenishment import AutoReplenishmentService

    expire_metrics = await expire_articles(db)
    repl_metrics = await AutoReplenishmentService.trigger_replenishment_if_needed(db, force=True)
    await _backfill_missing_thumbnails(db)
    homepage_articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
    category_desks = await HomepageBuilder.build_and_persist_category_desks(db)
    await CacheService.invalidate_homepage_cache(reason="manual_rebuild_endpoint")

    return {
        "status": "success",
        "message": "Editorial projections successfully rebuilt.",
        "expired_metrics": expire_metrics,
        "replenishment_metrics": repl_metrics,
        "homepage_article_count": len(homepage_articles),
        "homepage_articles": [{"id": a.id, "title": a.title, "thumbnail": a.thumbnail_url} for a in homepage_articles[:12]],
        "category_desks_count": len(category_desks),
    }


@router.api_route("/flush-and-crawl", methods=["GET", "POST"])
async def trigger_flush_and_crawl(db: AsyncSession = Depends(get_db)):
    """
    Purges expired articles, triggers a full live crawl across all active RSS sources,
    enriches with Gemini AI, and generates fresh homepage and category desks.
    """
    from app.services.ranking.news_ranking_engine import expire_articles
    from app.services.ingestion.replenishment import AutoReplenishmentService
    from app.editorial.homepage_builder import HomepageBuilder
    from app.services.cache_service import CacheService

    expire_metrics = await expire_articles(db)
    repl_metrics = await AutoReplenishmentService.trigger_replenishment_if_needed(db, force=True)
    await _backfill_missing_thumbnails(db)
    homepage_articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
    category_desks = await HomepageBuilder.build_and_persist_category_desks(db)
    await CacheService.invalidate_homepage_cache(reason="flush_and_crawl_endpoint")

    return {
        "status": "success",
        "action": "flush_and_crawl",
        "expired": expire_metrics,
        "replenishment": repl_metrics,
        "fresh_homepage_count": len(homepage_articles),
        "articles": [{"id": a.id, "title": a.title, "thumbnail": a.thumbnail_url} for a in homepage_articles[:12]],
    }

