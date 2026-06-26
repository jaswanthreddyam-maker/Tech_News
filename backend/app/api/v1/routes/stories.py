from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.story import Story, StoryStatus
from app.core.events.models import EventOutbox

router = APIRouter()

# --- Pydantic Schemas ---
class StoryCreate(BaseModel):
    title: str = Field(..., description="Canonical title of the story")
    primary_article_id: str | None = None
    created_by: str | None = None

class StoryUpdate(BaseModel):
    title: str | None = None
    status: StoryStatus | None = None
    primary_article_id: str | None = None

class StoryResponse(BaseModel):
    id: str
    title: str
    status: StoryStatus
    impact_score: float | None
    primary_article_id: str | None
    created_by: str | None
    
    class Config:
        from_attributes = True

# --- API Endpoints ---

@router.post("", response_model=StoryResponse, status_code=201)
async def create_story(story_in: StoryCreate, db: AsyncSession = Depends(get_db)):
    """Create a new Story entity."""
    new_story = Story(
        title=story_in.title,
        primary_article_id=story_in.primary_article_id,
        created_by=story_in.created_by,
        status=StoryStatus.ACTIVE
    )
    db.add(new_story)
    await db.flush()
    
    # Emit domain event via CQRS Outbox
    event_payload = {
        "story_id": new_story.id,
        "title": new_story.title,
        "primary_article_id": new_story.primary_article_id,
        "created_by": new_story.created_by
    }
    db.add(EventOutbox(event_type="StoryCreated", payload=event_payload))
    
    await db.commit()
    await db.refresh(new_story)
    return new_story

@router.get("", response_model=List[StoryResponse])
async def list_stories(
    status: StoryStatus | None = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List stories with pagination and optional status filter."""
    stmt = select(Story).order_by(Story.updated_at.desc()).offset(skip).limit(limit)
    if status:
        stmt = stmt.where(Story.status == status)
        
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific Story by ID."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(story_id: str, story_in: StoryUpdate, db: AsyncSession = Depends(get_db)):
    """Update a Story entity."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
        
    update_data = story_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)
        
    await db.commit()
    await db.refresh(story)
    return story

class StoryMergeRequest(BaseModel):
    source_story_id: str
    merged_by: str
    reason: str

@router.post("/{target_id}/merge")
async def merge_story(target_id: str, req: StoryMergeRequest, db: AsyncSession = Depends(get_db)):
    """Merge a source story into a target story."""
    if target_id == req.source_story_id:
        raise HTTPException(status_code=400, detail="Cannot merge a story into itself")
        
    target_story = await db.get(Story, target_id)
    source_story = await db.get(Story, req.source_story_id)
    
    if not target_story or not source_story:
        raise HTTPException(status_code=404, detail="One or both stories not found")
        
    # Re-assign articles from source to target
    from app.models.article import ProcessedArticle
    stmt = update(ProcessedArticle).where(ProcessedArticle.story_id == req.source_story_id).values(story_id=target_id)
    res = await db.execute(stmt)
    merged_article_count = res.rowcount
    
    # Archive source story
    source_story.status = StoryStatus.ARCHIVED
    
    # Emit StoriesMerged event
    event_payload = {
        "story_id": target_id,
        "source_story_id": req.source_story_id,
        "merged_article_count": merged_article_count,
        "merged_by": req.merged_by,
        "reason": req.reason
    }
    db.add(EventOutbox(event_type="StoriesMerged", payload=event_payload))
    
    await db.commit()
    return {"message": "Stories merged successfully", "merged_article_count": merged_article_count}

class StoryTimelineEventResponse(BaseModel):
    id: int
    story_id: str
    event_type: str
    occurred_at: datetime
    article_id: str | None
    milestone_type: str | None
    payload: dict

    class Config:
        from_attributes = True

@router.get("/{story_id}/timeline", response_model=List[StoryTimelineEventResponse])
async def get_story_timeline(story_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve the event-sourced timeline for a story, strictly ordered by event occurrence."""
    from app.models.story import StoryTimelineEvent
    stmt = (
        select(StoryTimelineEvent)
        .where(StoryTimelineEvent.story_id == story_id)
        .order_by(StoryTimelineEvent.occurred_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
