from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.summary_generator import SummaryGenerator
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.security import get_current_user
from app.core.telemetry import track_event
from app.models.user import User
from app.schemas.ai_summary import StructuredSummary

router = APIRouter(prefix="/ai/summary", tags=["AI Summaries"])

@router.get("/{article_id}", response_model=StructuredSummary)
async def get_or_generate_summary(
    article_id: int,
    background_tasks: BackgroundTasks,
    force_refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    redis = get_redis_client()
    # Simplified cache key for the read-through cache
    cache_key = f"ai_summary:article:{article_id}"

    if not force_refresh:
        cached = await redis.get(cache_key)
        if cached:
            track_event("summary_cached", {"article_id": article_id, "cache_hit": True})
            return StructuredSummary.model_validate_json(cached)

    track_event("summary_requested", {"article_id": article_id, "cache_hit": False})

    # Generate on demand
    generator = SummaryGenerator()
    try:
        summary = await generator.generate(db, article_id)

        # Cache the result
        await redis.set(cache_key, summary.model_dump_json(), ex=86400) # 24h cache

        track_event("summary_generated", {"article_id": article_id})
        return summary
    except Exception as e:
        track_event("summary_failed", {"article_id": article_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {e!s}")
