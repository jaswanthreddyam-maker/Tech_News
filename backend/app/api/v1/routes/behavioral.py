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
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Retrieve reading sessions.
    Can filter by 'in_progress' to get incomplete articles for Resume Reading.
    """
    query = select(ReadingSession, ProcessedArticle.title, ProcessedArticle.slug).join(
        ProcessedArticle, ReadingSession.article_id == ProcessedArticle.id
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
                article_id=session.article_id,
                article_title=title,
                article_slug=slug,
                started_at=session.started_at,
                last_activity_at=session.last_activity_at,
                total_reading_seconds=session.total_reading_seconds,
                completion_percentage=session.completion_percentage,
                is_completed=session.is_completed,
            )
        )

    return response


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

    if not current_user and not anonymous_id:
        raise HTTPException(status_code=400, detail="Must provide authentication or anonymous_id")

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
