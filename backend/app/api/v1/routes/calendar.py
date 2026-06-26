from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.models.article import ArticleReadModel, PublicationStatus

router = APIRouter()

class CalendarEntry(BaseModel):
    article_id: str
    title: str
    scheduled_for: datetime
    scheduled_by: str | None
    story_id: str | None
    
    class Config:
        from_attributes = True

class CalendarResponse(BaseModel):
    upcoming_content: List[CalendarEntry]
    
@router.get("/upcoming", response_model=CalendarResponse)
async def get_upcoming_content(db: AsyncSession = Depends(get_db)):
    """
    Retrieve an ordered queue of upcoming scheduled content.
    Returns articles that are SCHEDULED and have a scheduled_for date in the future,
    ordered by scheduled_for ascending.
    """
    now = datetime.now(timezone.utc)
    
    stmt = (
        select(ArticleReadModel)
        .where(
            and_(
                ArticleReadModel.publication_status == PublicationStatus.SCHEDULED.value,
                ArticleReadModel.scheduled_for > now
            )
        )
        .order_by(ArticleReadModel.scheduled_for.asc())
        .limit(100)
    )
    
    result = await db.execute(stmt)
    articles = result.scalars().all()
    
    entries = []
    for article in articles:
        entries.append(CalendarEntry(
            article_id=article.id,
            title=article.title,
            scheduled_for=article.scheduled_for,
            scheduled_by=article.scheduled_by,
            story_id=article.story_id
        ))
        
    return CalendarResponse(upcoming_content=entries)
