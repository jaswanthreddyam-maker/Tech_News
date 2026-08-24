import logging
import re
from typing import List, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_optional
from app.models.user import User
from app.briefing.models import DailyBriefingSubscriber, DailyBriefingDelivery
from app.briefing.contracts import VALID_TOPICS
from app.briefing.service import (
    DailyBriefingService,
    verify_signed_click_token,
    get_public_web_base_url,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/briefing", tags=["Daily Briefing"])


# ---------------------------------------------------------------------------
# Request schemas with Strict Validation
# ---------------------------------------------------------------------------

class PreferenceUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    enabled: bool = True
    delivery_time: str = Field(default="08:00", description="Local delivery time in HH:MM format")
    timezone: str = Field(default="Asia/Kolkata", description="Valid IANA timezone identifier")
    story_count: int = Field(default=5, ge=1, le=10, description="Stories count in daily briefing")
    topics: List[str] = Field(
        default=["artificial-intelligence", "technology", "cybersecurity"],
        description="List of preferred technology topic slugs"
    )

    @field_validator("delivery_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", v):
            raise ValueError("delivery_time must be in valid HH:MM 24-hour format (e.g. '08:00', '18:30')")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_iana_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
            return v
        except ZoneInfoNotFoundError:
            raise ValueError(f"'{v}' is not a recognized IANA timezone identifier (e.g. 'America/New_York', 'Asia/Kolkata')")

    @field_validator("story_count")
    @classmethod
    def validate_story_count(cls, v: int) -> int:
        if v not in (3, 5, 10):
            return 5 if v < 8 else 10
        return v

    @field_validator("topics")
    @classmethod
    def validate_topics_subset(cls, v: List[str]) -> List[str]:
        cleaned = [t.strip().lower() for t in v if t.strip().lower() in VALID_TOPICS]
        return cleaned if cleaned else ["technology"]


class TestBriefingRequest(BaseModel):
    email: Optional[EmailStr] = None


class VerifyEmailRequest(BaseModel):
    email: Optional[EmailStr] = None


# ---------------------------------------------------------------------------
# GET /preferences
# ---------------------------------------------------------------------------

@router.get("/preferences")
async def get_briefing_preferences(
    email: Optional[str] = Query(None, description="Optional email for lookup if not authenticated"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get preferences and last delivery telemetry.
    If authenticated, resolves strictly by current_user.id.
    If unauthenticated, checks optional email or returns default guest preferences with 200 OK.
    """
    subscriber = None

    if current_user:
        subscriber = await DailyBriefingService.get_subscriber_for_user(
            db, user_id=str(current_user.id), email=current_user.email
        )
        await db.commit()
    elif email:
        email_clean = email.strip().lower()
        stmt = select(DailyBriefingSubscriber).where(DailyBriefingSubscriber.email == email_clean)
        res = await db.execute(stmt)
        subscriber = res.scalar_one_or_none()

    if not subscriber:
        # Default guest/unauthenticated response
        return {
            "email": email or "",
            "email_verified": False,
            "enabled": False,
            "delivery_time": "08:00",
            "timezone": "Asia/Kolkata",
            "story_count": 5,
            "topics": ["artificial-intelligence", "technology", "cybersecurity"],
            "last_delivery": None,
        }

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
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Save Daily Briefing preferences.
    INVARIANTS:
    1. Authenticated user resolves subscriber exclusively by current_user.id.
    2. Unauthenticated subscriber creation requires valid email in payload.
    3. Zero verification bypass: does NOT auto-verify unverified emails.
    """
    if current_user:
        subscriber = await DailyBriefingService.get_subscriber_for_user(
            db, user_id=str(current_user.id), email=current_user.email
        )
    else:
        if not req.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is required for Daily Briefing subscription.",
            )
        subscriber = await DailyBriefingService.get_or_create_subscriber(db, email=req.email)

    subscriber.delivery_time = req.delivery_time
    subscriber.timezone = req.timezone
    subscriber.story_count = req.story_count
    subscriber.topics = req.topics

    verification_needed = False
    if req.enabled:
        if subscriber.email_verified_at is not None:
            subscriber.enabled = True
        else:
            subscriber.enabled = False
            verification_needed = True
            # Automatically dispatch verification email on initial subscription
            await DailyBriefingService.send_verification_email(db, subscriber)
    else:
        subscriber.enabled = False

    await db.commit()
    await db.refresh(subscriber)

    message = "Daily Briefing preferences saved."
    if verification_needed:
        message = f"Subscription saved! A verification email has been sent to {subscriber.email}. Please verify to activate daily delivery."

    return {
        "status": "success",
        "message": message,
        "verification_required": verification_needed,
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
# POST /verify-email
# ---------------------------------------------------------------------------

@router.post("/verify-email")
async def request_email_verification(
    req: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Dispatch a verification email to the user's or requested email address."""
    if current_user:
        subscriber = await DailyBriefingService.get_subscriber_for_user(
            db, user_id=str(current_user.id), email=current_user.email
        )
    else:
        if not req.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is required.",
            )
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
    web_url = get_public_web_base_url()
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html>
<head><title>Email Verified — Tech News Today</title></head>
<body style="font-family:monospace;background:#0a0a0a;color:#e5e5e5;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
  <div style="text-align:center;max-width:400px;padding:32px;background:#12151e;border-radius:16px;border:1px solid rgba(255,255,255,0.1)">
    <div style="font-size:48px;color:#10b981">✓</div>
    <h1 style="color:#ffffff;font-size:24px;margin:16px 0 8px">Email Verified</h1>
    <p style="color:#a3a3a3;font-size:14px;line-height:1.5">
      Your subscription to Tech News Today's Daily Briefing is now active for <strong style="color:#ffffff">{subscriber.email}</strong>.
    </p>
    <a href="{web_url}/dashboard/settings" style="display:inline-block;margin-top:16px;padding:10px 20px;background:#3b82f6;color:#ffffff;border-radius:8px;text-decoration:none;font-weight:bold;font-size:13px">
      Manage Notification Preferences &rarr;
    </a>
  </div>
</body>
</html>""",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# GET /unsubscribe?token=...
# ---------------------------------------------------------------------------

@router.get("/unsubscribe")
async def unsubscribe_by_token(
    token: str = Query(..., description="Signed unsubscribe token from email footer"),
    db: AsyncSession = Depends(get_db),
):
    """Deterministic, multi-day valid signed unsubscribe link."""
    subscriber = await DailyBriefingService.unsubscribe_by_token(db, raw_token=token)
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired unsubscribe link.",
        )
    await db.commit()
    web_url = get_public_web_base_url()
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html>
<head><title>Unsubscribed — Tech News Today</title></head>
<body style="font-family:monospace;background:#0a0a0a;color:#e5e5e5;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
  <div style="text-align:center;max-width:400px;padding:32px;background:#12151e;border-radius:16px;border:1px solid rgba(255,255,255,0.1)">
    <div style="font-size:48px;color:#6b7280">✕</div>
    <h1 style="color:#ffffff;font-size:24px;margin:16px 0 8px">Unsubscribed</h1>
    <p style="color:#a3a3a3;font-size:14px;line-height:1.5">
      You have been unsubscribed from the Daily Briefing. You will not receive any more daily emails.
    </p>
    <a href="{web_url}/dashboard/settings" style="display:inline-block;margin-top:16px;padding:10px 20px;background:#262626;color:#ffffff;border-radius:8px;text-decoration:none;font-weight:bold;font-size:13px">
      Resubscribe in Settings &rarr;
    </a>
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
    current_user: User = Depends(get_current_user),
):
    """
    Trigger an immediate test briefing dispatch.
    INVARIANTS:
    - Normal users can ONLY send to their own verified email.
    - Only Admins can specify an arbitrary destination email.
    """
    target_email = current_user.email.strip().lower()

    if req.email and req.email.strip().lower() != target_email:
        user_role = str(getattr(current_user, "role", "")).lower()
        if user_role not in ("admin", "userrole.admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non-admin users may only dispatch test briefings to their verified account email.",
            )
        target_email = req.email.strip().lower()

    try:
        result = await DailyBriefingService.send_test_briefing(
            db, email=target_email, user_id=str(current_user.id)
        )
        await db.commit()
        return result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as e:
        logger.error(f"Error triggering test briefing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test briefing: {str(e)}",
        )


# ---------------------------------------------------------------------------
# GET /click/{signed_token}
# ---------------------------------------------------------------------------

@router.get("/click/{signed_token}")
async def handle_signed_click(
    signed_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Canonical click tracking endpoint.
    Verifies HMAC-signed token, increments engagement telemetry, and redirects.
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
            await db.commit()

    # Safety: open redirect guard
    if target_url.startswith("http://") or target_url.startswith("https://"):
        web_base = get_public_web_base_url().replace("http://", "").replace("https://", "")
        if not (web_base in target_url or "localhost" in target_url or "technewstoday" in target_url):
            target_url = "/"

    return RedirectResponse(url=target_url, status_code=307)
