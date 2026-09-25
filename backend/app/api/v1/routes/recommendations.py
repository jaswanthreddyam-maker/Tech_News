import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.similarity import find_similar_articles
from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.core.security import get_current_user_optional
from app.models.user import User
from app.schemas.responses import StandardResponse

logger = logging.getLogger("tech_news.recommendations")
router = APIRouter()


@router.get("", response_model=StandardResponse[list])
async def get_recommendations(
    history_ids: list[int] = Query(..., description="List of recently read article IDs"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Content-based recommendations.
    Takes the user's recently read articles, finds nearest neighbors,
    filters out the already read articles, and returns Top N.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    logger.info(f"API Recommendations: Generating for history {history_ids}")

    if not history_ids:
        return StandardResponse(correlation_id=correlation_id, data=[])

    # Compute a history hash for caching
    import hashlib
    import json
    from datetime import datetime, timedelta, timezone

    from app.core.redis import get_redis_client

    history_str = ",".join(str(i) for i in sorted(history_ids))
    history_hash = hashlib.md5(history_str.encode("utf-8")).hexdigest()
    cache_key = f"recommendations:{history_hash}:limit:{limit}"

    try:
        import asyncio
        redis = get_redis_client()
        if redis:
            cached_data = await asyncio.wait_for(redis.get(cache_key), timeout=0.05)
            if cached_data:
                logger.info("API Recommendations: Serving from cache")
                return StandardResponse(correlation_id=correlation_id, data=json.loads(cached_data))
    except Exception as e:
        logger.warning(f"Redis get failed in recommendations: {e}")

    # We use the most recently read article as the pivot for simplicity
    # (In the future, we could average the embeddings of the history_ids)
    pivot_id = history_ids[0]

    # Find similar articles
    similar_results = await find_similar_articles(
        session=db,
        article_id=pivot_id,
        limit=limit * 5,  # overfetch for aggressive filtering
    )

    recommended = []
    seen_clusters = set()
    source_counts = {}
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=30)

    for art, sim_score in similar_results:
        if len(recommended) >= limit:
            break

        # 1. Remove already read articles
        if art.id in history_ids:
            continue

        # 2. Filter out articles older than 30 days
        if not art.published_at or art.published_at < cutoff_date:
            continue

        # 3. Filter duplicates via cluster_id (Max 1 per cluster)
        if art.cluster_id:
            if art.cluster_id in seen_clusters:
                continue
            seen_clusters.add(art.cluster_id)

        # 4. Diversity Limit: Max 2 per source
        source_name = art.source_name or art.source or "Unknown"
        if source_counts.get(source_name, 0) >= 2:
            continue
        source_counts[source_name] = source_counts.get(source_name, 0) + 1

        recommended.append(
            {
                "id": art.id,
                "title": art.title,
                "slug": art.slug,
                "summary": art.summary,
                "why_this_matters": getattr(art, "why_this_matters", None),
                "hero_image": art.hero_image or art.image_url,
                "source_name": source_name,
                "published_at": art.published_at.isoformat() if art.published_at else None,
                "similarity_score": round(sim_score, 4),
                "cluster_id": art.cluster_id,
            }
        )

    if not recommended:
        # Fallback 1: Topic and Entity graph matching based on recently read history
        from sqlalchemy import text
        try:
            art_id_strs = [str(x) for x in history_ids[:5]]
            query_sql = text("""
                WITH target_topics AS (
                    SELECT DISTINCT topic_name FROM tnt_article_topics WHERE article_id = ANY(:art_ids)
                ),
                target_entities AS (
                    SELECT DISTINCT entity_id FROM tnt_article_entities WHERE article_id = ANY(:art_ids)
                ),
                scored AS (
                    SELECT t.article_id, COUNT(*) * 3 as score
                    FROM tnt_article_topics t
                    WHERE t.topic_name IN (SELECT topic_name FROM target_topics)
                    AND t.article_id != ALL(:art_ids)
                    GROUP BY t.article_id
                    UNION ALL
                    SELECT e.article_id, COUNT(*) * 5 as score
                    FROM tnt_article_entities e
                    WHERE e.entity_id IN (SELECT entity_id FROM target_entities)
                    AND e.article_id != ALL(:art_ids)
                    GROUP BY e.article_id
                ),
                aggregated AS (
                    SELECT article_id, SUM(score) as total_score
                    FROM scored
                    GROUP BY article_id
                    ORDER BY total_score DESC
                    LIMIT :limit
                )
                SELECT a.id, a.title, a.slug, a.summary, a.thumbnail_url, a.thumbnail_local, a.source, a.published_at, agg.total_score
                FROM aggregated agg
                JOIN articles a ON a.id = agg.article_id
                WHERE a.is_test_data = false
            """)
            res = await db.execute(query_sql, {"art_ids": art_id_strs, "limit": limit})
            rows = res.fetchall()
            for r in rows:
                recommended.append({
                    "id": r.id,
                    "title": r.title,
                    "slug": r.slug or str(r.id),
                    "summary": r.summary,
                    "why_this_matters": None,
                    "hero_image": r.thumbnail_local or r.thumbnail_url,
                    "source_name": r.source or "Tech News",
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "similarity_score": round(min(0.95, float(r.total_score) / 10.0), 4),
                    "cluster_id": None
                })
        except Exception as exc:
            logger.warning(f"Topic/Entity graph recommendation fallback error: {exc}")

    # Fallback 2: Latest top articles excluding history
    if len(recommended) < limit:
        from app.models.article import ArticleReadModel
        from sqlalchemy import not_
        needed = limit - len(recommended)
        existing_rec_ids = {str(x["id"]) for x in recommended}
        exclude_ids = [str(x) for x in history_ids] + list(existing_rec_ids)
        stmt_fb = (
            select(ArticleReadModel)
            .where(
                ArticleReadModel.is_test_data == False,
                ArticleReadModel.publication_status == "PUBLISHED",
                not_(ArticleReadModel.id.in_(exclude_ids))
            )
            .order_by(ArticleReadModel.published_at.desc())
            .limit(needed)
        )
        fb_articles = (await db.execute(stmt_fb)).scalars().all()
        for art in fb_articles:
            recommended.append({
                "id": art.id,
                "title": art.title,
                "slug": art.slug or str(art.id),
                "summary": art.summary,
                "why_this_matters": getattr(art, "why_this_matters", None),
                "hero_image": art.thumbnail_local or art.thumbnail_url,
                "source_name": art.source or "Tech News",
                "published_at": art.published_at.isoformat() if art.published_at else None,
                "similarity_score": 0.75,
                "cluster_id": None,
            })

    if recommended:
        try:
            redis = get_redis_client()
            if redis:
                await redis.setex(cache_key, 900, json.dumps(recommended))  # 15 min TTL
        except Exception as e:
            logger.warning(f"Redis set failed in recommendations: {e}")

    logger.info(f"API Recommendations: Returning {len(recommended)} items")
    return StandardResponse(correlation_id=correlation_id, data=recommended)

from app.schemas.recommendations import RecommendationResponse
from app.services.recommendations.engine import RecommendationEngine


@router.get("/feed", response_model=StandardResponse[list[RecommendationResponse]])
async def get_personalized_feed(
    anonymous_id: str = Query(None, description="Anonymous device ID"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional)
):
    """
    Behavioral personalized feed using the Recommendation Engine.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    logger.info(f"API Feed: Generating feed for anon={anonymous_id}")

    user_id = user.id if user else None
    engine = RecommendationEngine()
    results = await engine.get_feed(session=db, user_id=user_id, anonymous_id=anonymous_id, limit=limit)

    return StandardResponse(correlation_id=correlation_id, data=results)
