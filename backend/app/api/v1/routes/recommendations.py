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
    limit: int = Query(10, ge=1, le=50),
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

    redis = get_redis_client()
    history_str = ",".join(str(i) for i in sorted(history_ids))
    history_hash = hashlib.md5(history_str.encode("utf-8")).hexdigest()
    cache_key = f"recommendations:{history_hash}:limit:{limit}"

    if redis:
        cached_data = await redis.get(cache_key)
        if cached_data:
            logger.info("API Recommendations: Serving from cache")
            return StandardResponse(correlation_id=correlation_id, data=json.loads(cached_data))

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

    if redis and recommended:
        await redis.setex(cache_key, 900, json.dumps(recommended))  # 15 min TTL

    logger.info(f"API Recommendations: Returning {len(recommended)} items")
    return StandardResponse(correlation_id=correlation_id, data=recommended)

from app.schemas.recommendations import RecommendationResponse
from app.services.recommendations.engine import RecommendationEngine


@router.get("/feed", response_model=StandardResponse[list[RecommendationResponse]])
async def get_personalized_feed(
    anonymous_id: str = Query(None, description="Anonymous device ID"),
    limit: int = Query(10, ge=1, le=50),
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
