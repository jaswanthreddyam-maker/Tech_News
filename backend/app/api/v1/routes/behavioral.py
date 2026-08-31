from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_optional
from app.models.article import ProcessedArticle
from app.models.behavioral import ReadingSession
from app.models.user import User
from app.schemas.behavioral import BehavioralBatchRequest, ReadingSessionResponse, UserInterestResponse
from app.services.behavioral.event_service import BehavioralEventService

router = APIRouter()


@router.post("/events")
async def ingest_behavioral_events(
    request: BehavioralBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Ingest a batch of behavioral events (idempotently).
    """
    user_id = current_user.id if current_user else None
    service = BehavioralEventService(db)
    result = await service.process_batch(request, user_id)
    return result


@router.get("/sessions", response_model=list[ReadingSessionResponse])
async def get_behavioral_sessions(
    status: str | None = Query(None, description="Filter by status (e.g., 'in_progress')"),
    limit: int = Query(10, le=50),
    anonymous_id: str | None = Query(None),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Retrieve reading sessions.
    Can filter by 'in_progress' to get incomplete articles for Resume Reading.
    """
    import asyncio
    import json
    from app.core.redis import get_redis_client

    user_key = str(current_user.id) if current_user else (anonymous_id or "none")
    cache_key = f"behavioral:v2:sessions:{user_key}:{status or 'all'}:{limit}"

    try:
        redis = get_redis_client()
        if redis:
            cached_data = await asyncio.wait_for(redis.get(cache_key), timeout=1.0)
            if cached_data:
                return json.loads(cached_data)
    except Exception:
        pass

    from app.core.database import safe_db_execute

    async def fetch_sessions(db):
        query = (
            select(ReadingSession, ProcessedArticle.title, ProcessedArticle.slug)
            .outerjoin(ProcessedArticle, ReadingSession.article_id == ProcessedArticle.id)
        )

        if current_user:
            query = query.where(ReadingSession.user_id == current_user.id)
        elif anonymous_id:
            query = query.where(ReadingSession.anonymous_id == anonymous_id)
        else:
            return []

        if status == "in_progress":
            query = query.where(ReadingSession.is_completed == False)

        query = query.order_by(ReadingSession.last_activity_at.desc()).limit(limit)

        result = await db.execute(query)
        results = result.all()

        response = []
        for session, title, slug in results:
            response.append(
                ReadingSessionResponse(
                    session_id=session.session_id,
                    article_id=session.article_id or 0,
                    article_title=title or "Continue Reading",
                    article_slug=slug or "",
                    started_at=session.started_at,
                    last_activity_at=session.last_activity_at,
                    total_reading_seconds=session.total_reading_seconds or 0,
                    completion_percentage=session.completion_percentage or 0,
                    is_completed=session.is_completed or False,
                )
            )
        return response

    try:
        response = await safe_db_execute(fetch_sessions)
        try:
            redis = get_redis_client()
            if redis:
                raw_payload = [r.model_dump(mode="json") for r in response]
                await asyncio.wait_for(redis.set(cache_key, json.dumps(raw_payload, default=str), ex=30), timeout=1.0)
        except Exception:
            pass

        return response
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"Error loading reading sessions: {exc}")
        return []


@router.get("/interests", response_model=list[UserInterestResponse])
async def get_user_interests(
    limit: int = Query(20, description="Max interests to return"),
    entity_type: str | None = Query(None, description="Filter by TOPIC, CATEGORY, etc."),
    anonymous_id: str | None = None,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve derived user interests.
    """
    from app.models.behavioral import UserInterest

    try:
        if not current_user and not anonymous_id:
            return []

        stmt = select(UserInterest)

        if current_user:
            stmt = stmt.where(UserInterest.user_id == current_user.id)
        else:
            stmt = stmt.where(UserInterest.anonymous_id == anonymous_id)

        if entity_type:
            stmt = stmt.where(UserInterest.entity_type == entity_type)

        stmt = stmt.order_by(UserInterest.affinity.desc()).limit(limit)

        result = await db.execute(stmt)
        interests = result.scalars().all()

        return [
            UserInterestResponse(
                entity_type=i.entity_type,
                entity_id=i.entity_id,
                affinity=i.affinity,
                expertise=i.expertise,
                confidence=i.confidence,
                model_version=i.model_version,
                last_updated=i.last_updated
            ) for i in interests
        ]
    except Exception as e:
        import logging
        logging.getLogger("tech_news.routes.behavioral").warning(f"Error querying user interests: {e}")
        return []
