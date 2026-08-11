import os
import hmac
import hashlib
import base64
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select, and_, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.briefing.models import (
    DailyBriefingSubscriber, DailyBriefingEdition, DailyBriefingItem,
    DailyBriefingDelivery, BriefingDeliveryStatus,
)
from app.briefing.selector import DailyBriefingSelector
from app.briefing.enricher import BriefingEnricher
from app.briefing.renderer import DailyBriefingRenderer
from app.notifications.email.provider import get_email_provider, EmailPayload
from app.core.events.models import EventOutbox

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Maximum items a global edition ever contains.
# Subscriber story_count preference is applied at render/dispatch time.
# ---------------------------------------------------------------------------
EDITION_MAX_CAPACITY = 10

SECRET_KEY = os.getenv("SECRET_KEY", "technews_daily_briefing_secure_hmac_secret_key_2026")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Token utilities
# ---------------------------------------------------------------------------

def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _sign_payload(payload_data: dict) -> str:
    """Sign a dict payload → base64url-payload.signature string."""
    json_bytes = json.dumps(payload_data, separators=(",", ":")).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(json_bytes).decode("utf-8").rstrip("=")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"{b64_payload}.{sig}"


def _verify_signed_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify HMAC-signed token and return decoded payload, or None on failure."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        b64_payload, sig = parts[0], parts[1]
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected_sig):
            return None
        padded = b64_payload + "=" * (-len(b64_payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        if datetime.now(timezone.utc).timestamp() > data.get("exp", 0):
            return None
        return data
    except Exception as e:
        logger.warning(f"Failed to verify signed token: {e}")
        return None


def create_signed_click_token(delivery_id: int, article_id: str, target_url: str) -> str:
    return _sign_payload({
        "type": "click",
        "did": delivery_id,
        "aid": article_id,
        "url": target_url,
        "exp": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
    })


def verify_signed_click_token(token: str) -> Optional[Dict[str, Any]]:
    return _verify_signed_token(token)


def create_signed_verification_token(subscriber_id: int, email: str) -> str:
    return _sign_payload({
        "type": "verify",
        "sid": subscriber_id,
        "email": email,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()),
    })


def create_signed_unsubscribe_token(subscriber_id: int, email: str) -> str:
    """Create a long-lived signed unsubscribe token (90 days)."""
    return _sign_payload({
        "type": "unsub",
        "sid": subscriber_id,
        "email": email,
        "exp": int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp()),
    })


# ---------------------------------------------------------------------------
# Timezone scheduling utility
# ---------------------------------------------------------------------------

def is_delivery_due(subscriber: "DailyBriefingSubscriber", now_utc: datetime, window_minutes: int = 5) -> bool:
    """
    Returns True if subscriber's configured delivery time falls within the
    current ±(window_minutes/2) window in their local timezone.
    """
    try:
        tz = ZoneInfo(subscriber.timezone)
    except ZoneInfoNotFoundError:
        logger.warning(f"Unknown timezone '{subscriber.timezone}' for subscriber {subscriber.id}. Skipping.")
        return False

    local_now = now_utc.astimezone(tz)
    try:
        h, m = map(int, subscriber.delivery_time.split(":"))
    except (ValueError, AttributeError):
        logger.warning(f"Invalid delivery_time '{subscriber.delivery_time}' for subscriber {subscriber.id}.")
        return False

    # Build the exact delivery datetime in local time today
    delivery_dt = local_now.replace(hour=h, minute=m, second=0, microsecond=0)

    half_window = timedelta(minutes=window_minutes / 2)
    return (delivery_dt - half_window) <= local_now <= (delivery_dt + half_window)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DailyBriefingService:
    """
    Core domain service for Daily Briefing: subscriber management, edition
    generation (always at max capacity), delivery dispatch, verification,
    unsubscribe, and timezone-aware scheduling.
    """

    # ------------------------------------------------------------------
    # Subscriber management
    # ------------------------------------------------------------------

    @classmethod
    async def get_or_create_subscriber(
        cls,
        db: AsyncSession,
        email: str,
        user_id: Optional[str] = None,
    ) -> DailyBriefingSubscriber:
        email_clean = email.strip().lower()
        stmt = select(DailyBriefingSubscriber).where(DailyBriefingSubscriber.email == email_clean)
        res = await db.execute(stmt)
        subscriber = res.scalar_one_or_none()

        if not subscriber:
            # Unsubscribe token: raw token is emailed; only hash stored in DB
            raw_unsub_token = f"unsub_{email_clean}_{os.urandom(12).hex()}"
            subscriber = DailyBriefingSubscriber(
                user_id=user_id,
                email=email_clean,
                enabled=False,  # Requires email verification
                delivery_time="08:00",
                timezone="Asia/Kolkata",
                story_count=5,
                topics=["artificial-intelligence", "technology", "cybersecurity"],
                unsubscribe_token_hash=hash_token(raw_unsub_token),
            )
            db.add(subscriber)
            await db.flush()

        elif user_id and not subscriber.user_id:
            # Bind authenticated user to existing subscriber if not already bound
            subscriber.user_id = user_id
            await db.flush()

        return subscriber

    @classmethod
    async def bind_user_to_subscriber(
        cls,
        db: AsyncSession,
        subscriber: "DailyBriefingSubscriber",
        user_id: str,
    ) -> None:
        """Associate an authenticated user account with a subscriber record."""
        if subscriber.user_id and subscriber.user_id != user_id:
            logger.warning(
                f"Subscriber {subscriber.id} already bound to user {subscriber.user_id}; "
                f"attempted rebind to {user_id} ignored."
            )
            return
        subscriber.user_id = user_id
        await db.flush()

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    @classmethod
    async def send_verification_email(
        cls,
        db: AsyncSession,
        subscriber: "DailyBriefingSubscriber",
    ) -> None:
        """Generate a signed verification token, store its hash, and dispatch the verification email."""
        raw_token = create_signed_verification_token(subscriber.id, subscriber.email)
        subscriber.verification_token_hash = hash_token(raw_token)
        subscriber.verification_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        await db.flush()

        verify_url = f"{BASE_URL}/api/v1/briefing/verify?token={raw_token}"
        provider = get_email_provider()
        payload = EmailPayload(
            to=subscriber.email,
            subject="Confirm your Daily Briefing subscription",
            html=f"""
<div style="font-family:monospace;background:#0a0a0a;color:#e5e5e5;padding:32px;max-width:480px;border-radius:12px">
  <p style="font-size:20px;font-weight:bold;color:#ffffff">Confirm Your Daily Briefing</p>
  <p style="color:#a3a3a3;font-size:14px">
    You've signed up to receive Tech News Today's Daily Briefing.
    Click below to verify your email and activate your subscription.
  </p>
  <a href="{verify_url}" style="display:inline-block;margin:16px 0;padding:12px 24px;background:#ffffff;color:#0a0a0a;border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px">
    Verify Email Address
  </a>
  <p style="color:#525252;font-size:12px">This link expires in 24 hours. If you didn't sign up, ignore this email.</p>
</div>""",
            text=f"Confirm your Daily Briefing subscription:\n\n{verify_url}\n\nExpires in 24 hours.",
            idempotency_key=f"verify-email:{subscriber.id}:{int(datetime.now(timezone.utc).timestamp())}",
            tags={"type": "verification", "subscriber_id": str(subscriber.id)},
        )
        result = await provider.send(payload)
        if not result.success:
            logger.error(f"Failed to send verification email to {subscriber.email}: {result.error}")

    @classmethod
    async def verify_email_token(
        cls,
        db: AsyncSession,
        raw_token: str,
    ) -> Optional["DailyBriefingSubscriber"]:
        """Validate signed verification token; mark subscriber as verified + enabled."""
        data = _verify_signed_token(raw_token)
        if not data or data.get("type") != "verify":
            return None

        subscriber_id = data.get("sid")
        token_hash = hash_token(raw_token)

        stmt = select(DailyBriefingSubscriber).where(
            and_(
                DailyBriefingSubscriber.id == subscriber_id,
                DailyBriefingSubscriber.verification_token_hash == token_hash,
            )
        )
        res = await db.execute(stmt)
        subscriber = res.scalar_one_or_none()

        if not subscriber:
            return None

        subscriber.email_verified_at = datetime.now(timezone.utc)
        subscriber.enabled = True
        subscriber.verification_token_hash = None
        subscriber.verification_expires_at = None
        await db.flush()
        return subscriber

    # ------------------------------------------------------------------
    # Unsubscribe
    # ------------------------------------------------------------------

    @classmethod
    async def unsubscribe_by_token(
        cls,
        db: AsyncSession,
        raw_token: str,
    ) -> Optional["DailyBriefingSubscriber"]:
        """
        Validate raw HMAC-signed unsubscribe token (from email URL).
        Hashes it server-side to compare against stored unsubscribe_token_hash.
        """
        data = _verify_signed_token(raw_token)
        if not data or data.get("type") != "unsub":
            return None

        subscriber_id = data.get("sid")
        token_hash = hash_token(raw_token)

        stmt = select(DailyBriefingSubscriber).where(
            and_(
                DailyBriefingSubscriber.id == subscriber_id,
                DailyBriefingSubscriber.unsubscribe_token_hash == token_hash,
            )
        )
        res = await db.execute(stmt)
        subscriber = res.scalar_one_or_none()

        if not subscriber:
            return None

        subscriber.enabled = False
        subscriber.unsubscribed_at = datetime.now(timezone.utc)
        await db.flush()
        return subscriber

    # ------------------------------------------------------------------
    # Edition (always generated at EDITION_MAX_CAPACITY = 10)
    # ------------------------------------------------------------------

    @classmethod
    async def get_or_create_daily_edition(
        cls,
        db: AsyncSession,
        edition_date: Optional[str] = None,
    ) -> "DailyBriefingEdition":
        """
        Get today's edition or create/re-evaluate it.

        INVARIANTS:
        1. Existing editions with items > 0 OR successful SENT/DELIVERED deliveries are immutable.
        2. Existing 0-item editions with NO successful deliveries are re-evaluated against selector.
        3. Newly generated 0-story selections do not poison future runs.
        """
        if not edition_date:
            edition_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        stmt = select(DailyBriefingEdition).where(DailyBriefingEdition.edition_date == edition_date)
        res = await db.execute(stmt)
        edition = res.scalar_one_or_none()

        if edition:
            stmt_items = (
                select(DailyBriefingItem)
                .where(DailyBriefingItem.edition_id == edition.id)
                .order_by(DailyBriefingItem.rank)
            )
            items_res = await db.execute(stmt_items)
            items = list(items_res.scalars().all())
            edition.loaded_items = items

            stmt_sent = (
                select(func.count(DailyBriefingDelivery.id))
                .where(
                    and_(
                        DailyBriefingDelivery.edition_id == edition.id,
                        DailyBriefingDelivery.status.in_([
                            BriefingDeliveryStatus.SENT,
                            BriefingDeliveryStatus.DELIVERED,
                        ]),
                    )
                )
            )
            sent_count = (await db.scalar(stmt_sent)) or 0

            # Reuse cached edition if it contains stories OR has already been sent to subscribers
            if len(items) > 0 or sent_count > 0:
                return edition

        # Always generate at maximum capacity — subscriber preference is applied later
        selected_articles = await DailyBriefingSelector.select_top_stories(
            db, limit=EDITION_MAX_CAPACITY
        )

        enriched_data = await BriefingEnricher.enrich_articles(selected_articles)

        selection_hash = hashlib.sha256(
            "-".join([item["article_id"] for item in enriched_data]).encode("utf-8")
        ).hexdigest()

        if not edition:
            edition_status = "PUBLISHED" if enriched_data else "EMPTY"
            edition = DailyBriefingEdition(
                edition_date=edition_date,
                selection_hash=selection_hash,
                algorithm_version="v2.2",
                status=edition_status,
            )
            db.add(edition)
            await db.flush()
        else:
            edition.selection_hash = selection_hash
            edition.status = "PUBLISHED" if enriched_data else "EMPTY"
            await db.execute(delete(DailyBriefingItem).where(DailyBriefingItem.edition_id == edition.id))
            await db.flush()

        item_models = []
        for item in enriched_data:
            b_item = DailyBriefingItem(
                edition_id=edition.id,
                article_id=item["article_id"],
                cluster_id=item["cluster_id"],
                rank=item["rank"],
                headline=item["headline"],
                why_it_matters=item["why_it_matters"],
                category=item["category"],
                source=item["source"],
                url=item["url"],
                read_time=item["read_time"],
            )
            db.add(b_item)
            item_models.append(b_item)
        await db.flush()
        edition.loaded_items = item_models

        # Transactional outbox event only for non-empty edition generation
        if item_models:
            outbox_event = EventOutbox(
                event_type="DailyBriefingGenerated",
                payload={
                    "edition_id": edition.id,
                    "edition_date": edition.edition_date,
                    "story_count": len(item_models),
                    "selection_hash": selection_hash,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            db.add(outbox_event)
            await db.flush()

        logger.info(
            f"DailyBriefingService: Edition {edition.id} ({edition_date}) "
            f"has {len(item_models)} items at max capacity {EDITION_MAX_CAPACITY}."
        )
        return edition

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    @classmethod
    async def dispatch_delivery(
        cls,
        db: AsyncSession,
        edition: "DailyBriefingEdition",
        subscriber: "DailyBriefingSubscriber",
        is_test: bool = False,
    ) -> "DailyBriefingDelivery":
        """
        Dispatch (or re-dispatch for test) one delivery.

        - Non-test sends require email_verified_at to be set.
        - Edition always has up to 10 items; subscriber receives items[:story_count].
        - Click tracking uses our signed route; provider webhooks do not count clicks.
        """
        if not is_test and not subscriber.email_verified_at:
            raise ValueError(
                f"Cannot dispatch to {subscriber.email}: email not verified."
            )

        # Idempotency check
        stmt_check = select(DailyBriefingDelivery).where(
            and_(
                DailyBriefingDelivery.edition_id == edition.id,
                DailyBriefingDelivery.subscriber_id == subscriber.id,
            )
        )
        res_check = await db.execute(stmt_check)
        existing_delivery = res_check.scalar_one_or_none()

        if existing_delivery and not is_test:
            logger.info(
                f"DailyBriefingService: Delivery already exists for subscriber "
                f"{subscriber.id} & edition {edition.id}. Skipping."
            )
            return existing_delivery

        idempotency_key = f"daily-briefing:{edition.id}:{subscriber.id}"
        if is_test:
            idempotency_key = (
                f"test-briefing:{edition.id}:{subscriber.id}:"
                f"{int(datetime.now(timezone.utc).timestamp())}"
            )

        if existing_delivery and is_test:
            # Reuse existing record for re-send (avoids UNIQUE constraint violation)
            delivery = existing_delivery
            delivery.status = BriefingDeliveryStatus.QUEUED
            delivery.provider_idempotency_key = idempotency_key
        else:
            delivery = DailyBriefingDelivery(
                edition_id=edition.id,
                subscriber_id=subscriber.id,
                email=subscriber.email,
                status=BriefingDeliveryStatus.QUEUED,
                provider_idempotency_key=idempotency_key,
                stories_delivered=subscriber.story_count,
            )
            db.add(delivery)
        await db.flush()

        # Load edition items
        items = getattr(edition, "loaded_items", [])
        if not items:
            stmt_items = (
                select(DailyBriefingItem)
                .where(DailyBriefingItem.edition_id == edition.id)
                .order_by(DailyBriefingItem.rank)
            )
            items_res = await db.execute(stmt_items)
            items = list(items_res.scalars().all())

        # Apply subscriber preference slice — this is where story_count matters
        items = items[:subscriber.story_count]
        delivery.stories_delivered = len(items)

        items_dict = [
            {
                "rank": it.rank,
                "article_id": it.article_id,
                "headline": it.headline,
                "why_it_matters": it.why_it_matters,
                "category": it.category,
                "source": it.source,
                "url": it.url or f"/articles/{it.article_id}",
                "read_time": it.read_time,
            }
            for it in items
        ]

        def click_url_builder(art_id: str, target_url: str) -> str:
            signed_token = create_signed_click_token(delivery.id, art_id, target_url)
            return f"{BASE_URL}/api/v1/briefing/click/{signed_token}"

        # Unsubscribe URL uses a freshly signed raw token (hash stored in DB)
        raw_unsub_token = create_signed_unsubscribe_token(subscriber.id, subscriber.email)
        subscriber.unsubscribe_token_hash = hash_token(raw_unsub_token)
        unsubscribe_url = f"{BASE_URL}/api/v1/briefing/unsubscribe?token={raw_unsub_token}"

        rendered = DailyBriefingRenderer.render_email(
            edition_date=edition.edition_date,
            items=items_dict,
            subscriber_email=subscriber.email,
            click_url_builder=click_url_builder,
            unsubscribe_url=unsubscribe_url,
        )

        email_payload = EmailPayload(
            to=subscriber.email,
            subject=rendered["subject"],
            html=rendered["html"],
            text=rendered["text"],
            idempotency_key=idempotency_key,
            tags={
                "edition_id": str(edition.id),
                "subscriber_id": str(subscriber.id),
                "type": "daily_briefing",
            },
        )

        provider = get_email_provider()
        result = await provider.send(email_payload)

        if result.success:
            delivery.status = BriefingDeliveryStatus.SENT
            delivery.provider_message_id = result.message_id
            delivery.sent_at = datetime.now(timezone.utc)
        else:
            delivery.status = BriefingDeliveryStatus.FAILED
            delivery.error_message = result.error

        await db.flush()
        return delivery

    # ------------------------------------------------------------------
    # Test send (bypasses verification gate)
    # ------------------------------------------------------------------

    @classmethod
    async def send_test_briefing(
        cls,
        db: AsyncSession,
        email: str,
    ) -> Dict[str, Any]:
        subscriber = await cls.get_or_create_subscriber(db, email=email)
        # Auto-verify for test dispatch so UI is immediately usable in dev
        if not subscriber.email_verified_at:
            subscriber.email_verified_at = datetime.now(timezone.utc)
            subscriber.enabled = True
            await db.flush()

        edition = await cls.get_or_create_daily_edition(db)
        delivery = await cls.dispatch_delivery(
            db, edition=edition, subscriber=subscriber, is_test=True
        )
        return {
            "status": "success",
            "message": f"Test briefing for {edition.edition_date} dispatched to {email}.",
            "delivery_id": delivery.id,
            "provider_message_id": delivery.provider_message_id,
            "delivery_status": delivery.status,
            "stories_delivered": delivery.stories_delivered,
        }

    # ------------------------------------------------------------------
    # Timezone-aware scheduler (called by Celery every 5 minutes)
    # ------------------------------------------------------------------

    @classmethod
    async def dispatch_due_subscribers(
        cls,
        db: AsyncSession,
        now_utc: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        Find all enabled, verified subscribers whose local delivery_time
        falls within the current 5-minute window and dispatch today's edition.
        UNIQUE(subscriber_id, edition_id) ensures idempotency on repeated calls.
        """
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)

        edition_date = now_utc.strftime("%Y-%m-%d")

        # Get/create today's edition (always at max capacity)
        edition = await cls.get_or_create_daily_edition(db, edition_date=edition_date)
        await db.flush()

        # Load eligible subscribers
        stmt = select(DailyBriefingSubscriber).where(
            and_(
                DailyBriefingSubscriber.enabled == True,
                DailyBriefingSubscriber.email_verified_at.isnot(None),
                DailyBriefingSubscriber.unsubscribed_at.is_(None),
            )
        )
        res = await db.execute(stmt)
        subscribers = list(res.scalars().all())

        dispatched = 0
        skipped_not_due = 0
        skipped_already_sent = 0
        errors = 0

        for subscriber in subscribers:
            if not is_delivery_due(subscriber, now_utc):
                skipped_not_due += 1
                continue

            try:
                delivery = await cls.dispatch_delivery(
                    db, edition=edition, subscriber=subscriber, is_test=False
                )
                if delivery.status == BriefingDeliveryStatus.SENT:
                    dispatched += 1
                else:
                    skipped_already_sent += 1
            except Exception as e:
                logger.error(
                    f"DailyBriefingService: Dispatch failed for subscriber "
                    f"{subscriber.id} ({subscriber.email}): {e}"
                )
                errors += 1

        await db.commit()
        logger.info(
            f"dispatch_due_subscribers: dispatched={dispatched}, "
            f"not_due={skipped_not_due}, already_sent={skipped_already_sent}, errors={errors}"
        )
        return {
            "dispatched": dispatched,
            "skipped_not_due": skipped_not_due,
            "skipped_already_sent": skipped_already_sent,
            "errors": errors,
        }
