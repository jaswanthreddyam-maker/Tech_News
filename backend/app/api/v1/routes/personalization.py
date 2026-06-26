from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.news import ArticleCard
from app.services.personalization_service import PersonalizationService

router = APIRouter()

class ReadingHistoryPayload(BaseModel):
    article_id: str
    progress: float
    completed: bool
    reading_time_seconds: int

class FeedItemResponse(BaseModel):
    article: ArticleCard
    reasoning_metadata: dict
    score: float

class ToggleResponse(BaseModel):
    status: str
    active: bool

@router.post("/saved/{article_id}", response_model=ToggleResponse)
async def toggle_saved_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    active = await service.toggle_saved_article(current_user.id, article_id)
    return ToggleResponse(status="success", active=active)

@router.post("/following/entities/{entity_id}", response_model=ToggleResponse)
async def toggle_followed_entity(
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    active = await service.toggle_followed_entity(current_user.id, entity_id)
    return ToggleResponse(status="success", active=active)

@router.post("/following/topics/{topic_name}", response_model=ToggleResponse)
async def toggle_followed_topic(
    topic_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    active = await service.toggle_followed_topic(current_user.id, topic_name)
    return ToggleResponse(status="success", active=active)

@router.get("/saved")
async def get_saved_articles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select

    from app.models.user import SavedArticle
    stmt = select(SavedArticle.article_id).where(SavedArticle.user_id == current_user.id)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/following/entities")
async def get_followed_entities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    entities = await service.get_followed_entities(current_user.id)
    return [{"id": e.id, "canonical_name": e.canonical_name, "entity_type": e.entity_type} for e in entities]

@router.get("/following/topics")
async def get_followed_topics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    topics = await service.get_followed_topics(current_user.id)
    return [{"name": t.name, "taxonomy_category": t.taxonomy_category} for t in topics]

@router.post("/history")
async def record_reading_history(
    payload: ReadingHistoryPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    history = await service.record_reading_history(
        user_id=current_user.id,
        article_id=payload.article_id,
        progress=payload.progress,
        completed=payload.completed,
        reading_time_seconds=payload.reading_time_seconds
    )
    return {"status": "success"}

@router.get("/feed", response_model=list[FeedItemResponse])
async def get_personalized_feed(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = PersonalizationService(db)
    feed = await service.get_personalized_feed(current_user.id, limit=limit, offset=offset)
    return feed
