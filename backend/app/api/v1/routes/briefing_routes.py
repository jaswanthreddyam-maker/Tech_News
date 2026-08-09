import logging
from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.briefing.models import DailyBriefingSubscriber, DailyBriefingDelivery, can_transition
from app.briefing.service import (
    DailyBriefingService,
    verify_signed_click_token,
    hash_token,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/briefing", tags=["Daily Briefing"])


# ---------------------------------------------------------------------------
# Auth helper — optional with hard error on bad JWT
# ---------------------------------------------------------------------------

async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Returns the authenticated User if a valid Bearer token is present.
    - No Authorization header  → None (anonymous subscriber allowed)
    - Valid Bearer token       → User object
    - Authorization present but invalid/expired → raises 401 (no silent downgrade)
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization format. Expected: Bearer <token>",
        )
    token = auth_header[7:]
    try:
        payload = decode_access_token(token)
    except HTTPException:
        raise  # Propagate 401 — don't silently downgrade
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject.")
    user = await db.get(User, int(user_id_str))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class PreferenceUpdateRequest(BaseModel):
    email: EmailStr
    enabled: bool = True
    delivery_time: str = "08:00"
    timezone: str = "Asia/Kolkata"
    story_count: int = 5
    topics: List[str] = ["artificial-intelligence", "technology", "cybersecurity"]


class TestBriefingRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    email: EmailStr


# ---------------------------------------------------------------------------
# GET /preferences
# ---------------------------------------------------------------------------

@router.get("/preferences")
async def get_briefing_preferences(
    email: str = Query("user@example.com", description="Subscriber email"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get preferences and last delivery telemetry for a Daily Briefing subscriber."""
    # Authenticated: look up by user_id first, fall back to email
    subscriber = None
    if current_user:
        stmt = select(DailyBriefingSubscriber).where(
            DailyBriefingSubscriber.user_id == str(current_user.id)
        )
        res = await db.execute(stmt)
        subscriber = res.scalar_one_or_none()

    if not subscriber:
        subscriber = await DailyBriefingService.get_or_create_subscriber(
            db, email=email, user_id=str(current_user.id) if current_user else None
        )
        await db.commit()

    # Last delivery telemetry
    stmt_del = (
        select(DailyBriefingDelivery)
        .where(DailyBriefingDelivery.subscriber_id == subscriber.id)
        .order_by(DailyBriefingDelivery.created_at.desc())
        .limit(1)
    )
    del_res = await db.execute(stmt_del)
    last_delivery = del_res.scalar_one_or_none()

    telemetry = None
    if last_delivery:
        delivered_dt = last_delivery.sent_at or last_delivery.created_at
        telemetry = {
            "delivered_at": delivered_dt.isoformat() if delivered_dt else None,
            "status": str(last_delivery.status.value if hasattr(last_delivery.status, "value") else last_delivery.status),
            "provider_message_id": last_delivery.provider_message_id,
            "stories_count": last_delivery.stories_delivered,
        }

    return {
        "email": subscriber.email,
        "email_verified": subscriber.email_verified_at is not None,
        "enabled": subscriber.enabled,
        "delivery_time": subscriber.delivery_time,
        "timezone": subscriber.timezone,
        "story_count": subscriber.story_count,
        "topics": subscriber.topics,
        "last_delivery": telemetry,
    }


# ---------------------------------------------------------------------------
# POST /preferences
# ---------------------------------------------------------------------------

@router.post("/preferences")
async def update_briefing_preferences(
    req: PreferenceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Update preferences for Daily Briefing. Binds to authenticated user if JWT present."""
    user_id = str(current_user.id) if current_user else None
    subscriber = await DailyBriefingService.get_or_create_subscriber(
        db, email=req.email, user_id=user_id
    )

    # Bind user if authenticated and not yet bound
    if current_user and not subscriber.user_id:
        await DailyBriefingService.bind_user_to_subscriber(db, subscriber, str(current_user.id))

    subscriber.delivery_time = req.delivery_time
    subscriber.timezone = req.timezone
    subscriber.story_count = req.story_count
    subscriber.topics = req.topics

    # Only toggle enabled if email is verified; otherwise silently ignore enable=True
    if req.enabled and subscriber.email_verified_at:
        subscriber.enabled = True
    elif not req.enabled:
        subscriber.enabled = False

    await db.commit()
    await db.refresh(subscriber)

    return {
        "status": "success",
        "message": "Daily Briefing preferences saved.",
        "preferences": {
            "email": subscriber.email,
            "email_verified": subscriber.email_verified_at is not None,
            "enabled": subscriber.enabled,
            "delivery_time": subscriber.delivery_time,
            "timezone": subscriber.timezone,
            "story_count": subscriber.story_count,
            "topics": subscriber.topics,
        },
    }


# ---------------------------------------------------------------------------
# POST /verify-email  — send verification email
# ---------------------------------------------------------------------------

@router.post("/verify-email")
async def request_email_verification(
    req: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Dispatch a verification email to the subscriber's address."""
    subscriber = await DailyBriefingService.get_or_create_subscriber(db, email=req.email)
    if subscriber.email_verified_at:
        return {"status": "already_verified", "message": "Email is already verified."}

    await DailyBriefingService.send_verification_email(db, subscriber)
    await db.commit()
    return {
        "status": "success",
        "message": f"Verification email sent to {subscriber.email}. Valid for 24 hours.",
    }


# ---------------------------------------------------------------------------
# GET /verify?token=...  — click-through email verification
# ---------------------------------------------------------------------------

@router.get("/verify")
async def verify_email(
    token: str = Query(..., description="Signed verification token from email"),
    db: AsyncSession = Depends(get_db),
):
    """Validate signed email verification token and activate subscription."""
    subscriber = await DailyBriefingService.verify_email_token(db, raw_token=token)
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link.",
        )
    await db.commit()
    return HTMLResponse(
        content=f"""
<!DOCTYPE html>
<html>
<head><title>Email Verified — Tech News Today</title></head>
<body style="font-family:monospace;background:#0a0a0a;color:#e5e5e5;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
  <div style="text-align:center;max-width:400px">
    <div style="font-size:48px">✓</div>
    <h1 style="color:#ffffff;font-size:24px;margin:16px 0 8px">Email Verified</h1>
    <p style="color:#a3a3a3;font-size:14px">Your Daily Briefing subscription for <strong>{subscriber.email}</strong> is now active.</p>
    <a href="http://localhost:3000/settings" style="display:inline-block;margin-top:24px;padding:10px 20px;background:#ffffff;color:#0a0a0a;border-radius:8px;text-decoration:none;font-size:13px;font-weight:bold">Go to Settings</a>
  </div>
</body>
</html>""",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# GET /unsubscribe?token=...  — one-click unsubscribe
# ---------------------------------------------------------------------------

@router.get("/unsubscribe")
async def unsubscribe(
    token: str = Query(..., description="Signed unsubscribe token from email"),
    db: AsyncSession = Depends(get_db),
):
    """
    One-click unsubscribe. Validates the raw HMAC-signed token from the email URL,
    hashes it server-side, and compares against the stored unsubscribe_token_hash.
    """
    subscriber = await DailyBriefingService.unsubscribe_by_token(db, raw_token=token)
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired unsubscribe link.",
        )
    await db.commit()
    return HTMLResponse(
        content=f"""
<!DOCTYPE html>
<html>
<head><title>Unsubscribed — Tech News Today</title></head>
<body style="font-family:monospace;background:#0a0a0a;color:#e5e5e5;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
  <div style="text-align:center;max-width:400px">
    <div style="font-size:48px">✓</div>
    <h1 style="color:#ffffff;font-size:24px;margin:16px 0 8px">Unsubscribed</h1>
    <p style="color:#a3a3a3;font-size:14px">You've been removed from the Daily Briefing for <strong>{subscriber.email}</strong>.</p>
    <p style="color:#525252;font-size:12px;margin-top:8px">You can resubscribe any time from Settings.</p>
  </div>
</body>
</html>""",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# POST /send-test
# ---------------------------------------------------------------------------

@router.post("/send-test")
async def send_test_briefing(
    req: TestBriefingRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate test briefing dispatch to the given email."""
    try:
        result = await DailyBriefingService.send_test_briefing(db, email=req.email)
        await db.commit()
        return result
    except Exception as e:
        logger.error(f"Error triggering test briefing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test briefing: {str(e)}",
        )


# ---------------------------------------------------------------------------
# GET /click/{signed_token}  — HMAC-signed click tracking
# ---------------------------------------------------------------------------

@router.get("/click/{signed_token}")
async def handle_signed_click(
    signed_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Canonical click tracking endpoint.
    Verifies HMAC-signed token, increments click_count + sets first_clicked_at
    (engagement telemetry, does NOT change delivery status), then redirects.
    """
    data = verify_signed_click_token(signed_token)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired click tracking token.",
        )

    delivery_id = data.get("did")
    target_url = data.get("url", "/")

    if delivery_id:
        stmt = select(DailyBriefingDelivery).where(DailyBriefingDelivery.id == delivery_id)
        res = await db.execute(stmt)
        delivery = res.scalar_one_or_none()
        if delivery:
            now_dt = datetime.now(timezone.utc)
            if not delivery.first_clicked_at:
                delivery.first_clicked_at = now_dt
            delivery.click_count = (delivery.click_count or 0) + 1
            # Delivery status is NOT changed — clicks are engagement, not lifecycle
            await db.commit()

    # Safety: reject open redirects to external domains
    if target_url.startswith("http://") or target_url.startswith("https://"):
        if not ("localhost" in target_url or "technewstoday" in target_url):
            target_url = "/"

    return RedirectResponse(url=target_url, status_code=307)
