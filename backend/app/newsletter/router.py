from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import base64
from app.core.database import get_db
from app.core.security import apply_rate_limit
from app.newsletter.schemas import (
    NewsletterSubscribeRequest, NewsletterResponse, NewsletterStatsResponse, 
    BriefingUpdateRequest, BriefingApprovalRequest, BriefingSchema, 
    CampaignSchema, CampaignAnalyticsSchema
)
from app.newsletter.service import NewsletterService
from app.newsletter.repository import NewsletterRepository

router = APIRouter()

@router.post("/subscribe", response_model=NewsletterResponse)
async def subscribe_newsletter(
    request: Request,
    payload: NewsletterSubscribeRequest,
    db: AsyncSession = Depends(get_db)
):
    # Apply IP-based rate limiting: 5 requests per minute
    await apply_rate_limit(request, action="newsletter_subscribe_ip", max_requests=5, window_seconds=60)
    
    # Apply Email-based rate limiting: 5 requests per hour
    await apply_rate_limit(request, action="newsletter_subscribe_email", max_requests=5, window_seconds=3600, identifier=payload.email)

    service = NewsletterService(db)
    await service.subscribe(email=payload.email)
    
    # Commit the transaction to persist the subscriber and outbox event
    await db.commit()
    
    return NewsletterResponse(
        success=True,
        message="Subscription confirmed."
    )

@router.get("/stats", response_model=NewsletterStatsResponse)
async def get_newsletter_stats(
    db: AsyncSession = Depends(get_db)
):
    # Usually you'd require admin privileges here, but we will rely on 
    # the frontend calling this from an admin page, or add simple role-based auth.
    repo = NewsletterRepository(db)
    stats = await repo.get_stats()
    
    total = stats.total_subscribers
    confirmed = stats.confirmed_subscribers
    unsubscribed = stats.unsubscribed
    
    rate = 0.0
    active_base = total - unsubscribed
    if active_base > 0:
        rate = (confirmed / active_base) * 100
        
    return NewsletterStatsResponse(
        total_subscribers=total,
        pending_subscribers=stats.pending_subscribers,
        confirmed_subscribers=confirmed,
        unsubscribed=stats.unsubscribed,
        confirmation_rate=round(rate, 1),
        new_today=0 # Simplified for now
    )

@router.get("/confirm/{token}")
async def confirm_subscription(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    service = NewsletterService(db)
    success = await service.confirm_subscription(token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation token.")
    
    await db.commit()
    # Usually we'd redirect to a frontend success page.
    return {"success": True, "message": "Subscription confirmed successfully!"}

@router.get("/unsubscribe/{token}")
async def unsubscribe(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    service = NewsletterService(db)
    success = await service.unsubscribe(token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token.")
        
    await db.commit()
    return {"success": True, "message": "You have been unsubscribed."}

# Transparent 1x1 GIF for email open tracking
TRANSPARENT_1X1_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

@router.get("/track/open/{delivery_id}.gif")
async def track_email_open(
    delivery_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = NewsletterService(db)
    await service.track_open(delivery_id)
    await db.commit()
    
    return Response(content=TRANSPARENT_1X1_GIF, media_type="image/gif")

@router.get("/track/click")
async def track_email_click(
    delivery_id: int,
    url: str,
    db: AsyncSession = Depends(get_db)
):
    service = NewsletterService(db)
    await service.track_click(delivery_id, url)
    await db.commit()
    
    # Redirect user to the destination URL
    return RedirectResponse(url=url)

@router.post("/webhooks/esp")
async def esp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # In production, verify the webhook signature here (e.g. Svix for Resend)
    payload = await request.json()
    service = NewsletterService(db)
    await service.process_esp_webhook(payload)
    await db.commit()
    
    return {"status": "ok"}

# --- Editorial Endpoints ---

@router.get("/briefings", response_model=list[BriefingSchema])
async def get_briefings(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.newsletter.models import NewsletterBriefing
    
    stmt = select(NewsletterBriefing).order_by(NewsletterBriefing.created_at.desc())
    result = await db.execute(stmt)
    briefings = result.scalars().all()
    
    # Normally we'd use selectinload on versions, but they aren't mapped with relationship() here.
    # We will fetch versions separately or just return the briefings.
    from app.newsletter.models import NewsletterBriefingVersion
    for b in briefings:
        v_stmt = select(NewsletterBriefingVersion).where(NewsletterBriefingVersion.briefing_id == b.id).order_by(NewsletterBriefingVersion.version_number.desc())
        v_result = await db.execute(v_stmt)
        b.versions = v_result.scalars().all()
        
    return briefings

@router.get("/campaigns", response_model=list[CampaignSchema])
async def get_campaigns(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.newsletter.models import NewsletterCampaign
    stmt = select(NewsletterCampaign).order_by(NewsletterCampaign.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/campaigns/{campaign_id}/analytics", response_model=CampaignAnalyticsSchema)
async def get_campaign_analytics(campaign_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.newsletter.models import CampaignAnalyticsProjection
    stmt = select(CampaignAnalyticsProjection).where(CampaignAnalyticsProjection.campaign_id == campaign_id)
    result = await db.execute(stmt)
    analytics = result.scalar_one_or_none()
    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics not found for campaign")
    return analytics

@router.put("/briefings/{id}")
async def update_draft_briefing(
    id: int,
    payload: BriefingUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    service = NewsletterService(db)
    # In production, extract editor_id from JWT token via dependency
    editor_id = "editor-1" 
    result = await service.update_briefing(id, payload.title, payload.content_html, payload.content_text, editor_id)
    await db.commit()
    return result

@router.post("/briefings/{id}/approve")
async def approve_briefing(
    id: int,
    payload: BriefingApprovalRequest | None = None,
    db: AsyncSession = Depends(get_db)
):
    service = NewsletterService(db)
    scheduled_at = payload.scheduled_at if payload else None
    success = await service.approve_briefing(id, scheduled_at=scheduled_at)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve briefing. Must exist and be DRAFT.")
    await db.commit()
    return {"success": True, "message": "Briefing approved."}

@router.post("/briefings/{id}/reject")
async def reject_briefing(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    service = NewsletterService(db)
    success = await service.reject_briefing(id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject briefing. Must exist and be DRAFT.")
    await db.commit()
    return {"success": True, "message": "Briefing rejected."}

@router.post("/briefings/{id}/archive")
async def archive_briefing(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    service = NewsletterService(db)
    success = await service.archive_briefing(id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to archive briefing.")
    await db.commit()
    return {"success": True, "message": "Briefing archived."}
