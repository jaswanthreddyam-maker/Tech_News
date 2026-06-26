from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.article import ProcessedArticle, EditorialStatus, PublicationStatus
from app.core.events.models import EventOutbox

router = APIRouter()

# --- Pydantic Schemas ---
class EventResponse(BaseModel):
    message: str
    article_id: int
    editorial_status: str
    publication_status: str | None
    
class ScheduleRequest(BaseModel):
    scheduled_for: datetime
    scheduled_by: str

class RejectRequest(BaseModel):
    reason: str
    rejected_by: str

# --- Helper functions for Events ---
async def _emit_event(db: AsyncSession, article_id: int, event_type: str, payload: dict):
    payload["article_id"] = article_id
    event = EventOutbox(
        event_type=event_type,
        payload=payload
    )
    db.add(event)

# --- Editorial Endpoints ---
@router.post("/{article_id}/editorial/submit", response_model=EventResponse)
async def submit_for_review(article_id: int, db: AsyncSession = Depends(get_db)):
    """Submit a DRAFT article for REVIEW."""
    article = await db.get(ProcessedArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if article.editorial_status != EditorialStatus.DRAFT and article.editorial_status != EditorialStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Only DRAFT or REJECTED articles can be submitted for review.")
        
    article.editorial_status = EditorialStatus.REVIEW
    await _emit_event(db, article_id, "ArticleSubmittedForReview", {
        "story_id": article.story_id,
        "editorial_status": EditorialStatus.REVIEW.value
    })
    await db.commit()
    
    return EventResponse(
        message="Article submitted for review.", 
        article_id=article_id, 
        editorial_status=article.editorial_status.value, 
        publication_status=article.publication_status.value if article.publication_status else None
    )

@router.post("/{article_id}/editorial/approve", response_model=EventResponse)
async def approve_article(article_id: int, db: AsyncSession = Depends(get_db)):
    """Approve an article in REVIEW."""
    article = await db.get(ProcessedArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if article.editorial_status != EditorialStatus.REVIEW:
        raise HTTPException(status_code=400, detail="Only REVIEW articles can be approved.")
        
    article.editorial_status = EditorialStatus.APPROVED
    await _emit_event(db, article_id, "ArticleApproved", {
        "story_id": article.story_id,
        "editorial_status": EditorialStatus.APPROVED.value
    })
    await db.commit()
    
    return EventResponse(
        message="Article approved.", 
        article_id=article_id, 
        editorial_status=article.editorial_status.value, 
        publication_status=article.publication_status.value if article.publication_status else None
    )

@router.post("/{article_id}/editorial/reject", response_model=EventResponse)
async def reject_article(article_id: int, req: RejectRequest, db: AsyncSession = Depends(get_db)):
    """Reject an article in REVIEW."""
    article = await db.get(ProcessedArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if article.editorial_status != EditorialStatus.REVIEW:
        raise HTTPException(status_code=400, detail="Only REVIEW articles can be rejected.")
        
    article.editorial_status = EditorialStatus.REJECTED
    await _emit_event(db, article_id, "ArticleRejected", {
        "story_id": article.story_id,
        "editorial_status": EditorialStatus.REJECTED.value,
        "reason": req.reason,
        "rejected_by": req.rejected_by
    })
    await db.commit()
    
    return EventResponse(
        message="Article rejected.", 
        article_id=article_id, 
        editorial_status=article.editorial_status.value, 
        publication_status=article.publication_status.value if article.publication_status else None
    )

# --- Publication Endpoints ---
@router.post("/{article_id}/publication/schedule", response_model=EventResponse)
async def schedule_article(article_id: int, req: ScheduleRequest, db: AsyncSession = Depends(get_db)):
    """Schedule an APPROVED article for publication."""
    article = await db.get(ProcessedArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if article.editorial_status != EditorialStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Article must be APPROVED before it can be scheduled.")
        
    article.publication_status = PublicationStatus.SCHEDULED
    article.scheduled_for = req.scheduled_for
    article.scheduled_by = req.scheduled_by
    await _emit_event(db, article_id, "ArticleScheduled", {
        "story_id": article.story_id,
        "publication_status": PublicationStatus.SCHEDULED.value,
        "scheduled_for": req.scheduled_for.isoformat(),
        "scheduled_by": req.scheduled_by
    })
    await db.commit()
    
    return EventResponse(
        message="Article scheduled.", 
        article_id=article_id, 
        editorial_status=article.editorial_status.value, 
        publication_status=article.publication_status.value
    )

@router.post("/{article_id}/publication/publish", response_model=EventResponse)
async def publish_article(article_id: int, db: AsyncSession = Depends(get_db)):
    """Publish an APPROVED or SCHEDULED article immediately."""
    article = await db.get(ProcessedArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if article.editorial_status != EditorialStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Article must be APPROVED before it can be published.")
        
    article.publication_status = PublicationStatus.PUBLISHED
    article.published_at = datetime.now(timezone.utc)
    
    # We still emit the standard ArticlePublished, but now it includes the status so the generic handler catches it.
    await _emit_event(db, article_id, "ArticlePublished", {
        "story_id": article.story_id,
        "publication_status": PublicationStatus.PUBLISHED.value,
        "published_at": article.published_at.isoformat()
    })
    await db.commit()
    
    return EventResponse(
        message="Article published.", 
        article_id=article_id, 
        editorial_status=article.editorial_status.value, 
        publication_status=article.publication_status.value
    )

@router.post("/{article_id}/publication/archive", response_model=EventResponse)
async def archive_article(article_id: int, db: AsyncSession = Depends(get_db)):
    """Archive a PUBLISHED article."""
    article = await db.get(ProcessedArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    if article.publication_status != PublicationStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Only PUBLISHED articles can be archived.")
        
    article.publication_status = PublicationStatus.ARCHIVED
    await _emit_event(db, article_id, "ArticleArchived", {
        "story_id": article.story_id,
        "publication_status": PublicationStatus.ARCHIVED.value
    })
    await db.commit()
    
    return EventResponse(
        message="Article archived.", 
        article_id=article_id, 
        editorial_status=article.editorial_status.value, 
        publication_status=article.publication_status.value
    )
