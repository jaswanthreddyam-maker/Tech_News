import logging
import hashlib
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.briefing.models import (
    WebhookEvent, DailyBriefingDelivery, BriefingDeliveryStatus,
    can_transition, BRIEFING_TERMINAL_STATES,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/resend")
async def handle_resend_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Inbound webhook endpoint for Resend email provider events.

    Idempotency: WebhookEvent table enforces UNIQUE(provider, event_id).

    State-transition protection: only valid forward transitions from the
    current delivery status are applied (e.g. BOUNCED cannot become DELIVERED).

    Click counting: email.clicked from Resend records provider_clicked_at for
    audit ONLY — it does NOT increment click_count. click_count is the canonical
    counter from our signed /click/{token} route to avoid double counting.
    """
    raw_body = await request.body()

    # Fail closed in Production environment: RESEND_WEBHOOK_SECRET is MANDATORY
    import os
    from app.core.config import settings

    is_production = settings.effective_environment == "production"
    webhook_secret = os.getenv("RESEND_WEBHOOK_SECRET")

    if is_production and not webhook_secret:
        logger.critical("Resend Webhook: RESEND_WEBHOOK_SECRET missing in PRODUCTION environment! Failing closed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret configuration missing in production",
        )

    if webhook_secret:
        svix_id = request.headers.get("svix-id")
        svix_timestamp = request.headers.get("svix-timestamp")
        svix_signature = request.headers.get("svix-signature")
        if not (svix_id and svix_timestamp and svix_signature):
            logger.warning("Resend Webhook: Missing required svix signature headers.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature headers",
            )

        # Verify HMAC signature against raw request body
        import hmac
        import base64
        signed_payload = f"{svix_id}.{svix_timestamp}.{raw_body.decode('utf-8')}"
        secret_bytes = base64.b64decode(webhook_secret.split("_")[-1]) if "_" in webhook_secret else webhook_secret.encode("utf-8")
        expected_sig = base64.b64encode(hmac.new(secret_bytes, signed_payload.encode("utf-8"), hashlib.sha256).digest()).decode("utf-8")

        passed = any(sig.split(",")[-1] == expected_sig or expected_sig in sig for sig in svix_signature.split(" "))
        if not passed:
            logger.error("Resend Webhook: Signature verification failed!")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )


    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_id = (
        payload.get("id")
        or payload.get("data", {}).get("email_id")
        or hashlib.md5(raw_body).hexdigest()
    )
    event_type = payload.get("type", "unknown")
    provider = "RESEND"


    # 1. Idempotency check
    stmt_evt = select(WebhookEvent).where(
        WebhookEvent.provider == provider,
        WebhookEvent.event_id == str(event_id),
    )
    evt_res = await db.execute(stmt_evt)
    if evt_res.scalar_one_or_none():
        logger.info(f"WebhookRouter: Event {event_id} already processed. Skipping.")
        return {"status": "ignored", "reason": "duplicate_event_id"}

    payload_hash = hashlib.sha256(raw_body).hexdigest()
    webhook_evt = WebhookEvent(
        provider=provider,
        event_id=str(event_id),
        event_type=event_type,
        payload_hash=payload_hash,
        processed_at=datetime.now(timezone.utc),
    )
    db.add(webhook_evt)

    # 2. Resolve delivery record
    data_payload = payload.get("data", {})
    email_id = data_payload.get("email_id") or data_payload.get("id")

    if email_id:
        stmt_del = select(DailyBriefingDelivery).where(
            DailyBriefingDelivery.provider_message_id == str(email_id)
        )
        del_res = await db.execute(stmt_del)
        delivery = del_res.scalar_one_or_none()

        if delivery:
            now_dt = datetime.now(timezone.utc)
            current_status = delivery.status

            # Map Resend event_type → target lifecycle status
            status_map = {
                "email.sent":      BriefingDeliveryStatus.SENT,
                "email.delivered": BriefingDeliveryStatus.DELIVERED,
                "email.bounced":   BriefingDeliveryStatus.BOUNCED,
                "email.complained": BriefingDeliveryStatus.COMPLAINED,
            }

            if event_type in status_map:
                target_status = status_map[event_type]
                if can_transition(current_status, target_status):
                    delivery.status = target_status
                    if target_status == BriefingDeliveryStatus.SENT:
                        delivery.sent_at = delivery.sent_at or now_dt
                    elif target_status == BriefingDeliveryStatus.DELIVERED:
                        delivery.delivered_at = now_dt
                    logger.info(
                        f"WebhookRouter: {current_status} → {target_status} "
                        f"for delivery {delivery.id}"
                    )
                else:
                    logger.warning(
                        f"WebhookRouter: Blocked invalid transition "
                        f"{current_status} → {target_status} for delivery {delivery.id}"
                    )

            elif event_type == "email.opened":
                # Open is engagement telemetry, does NOT change delivery status
                if not delivery.opened_observed_at:
                    delivery.opened_observed_at = now_dt
                logger.info(f"WebhookRouter: Open observed for delivery {delivery.id}")

            elif event_type == "email.clicked":
                # Provider click event = audit only.
                # click_count is owned by the signed /click/ route — not incremented here.
                if not delivery.provider_clicked_at:
                    delivery.provider_clicked_at = now_dt
                logger.info(
                    f"WebhookRouter: Provider click event recorded for delivery {delivery.id} "
                    f"(click_count NOT incremented — canonical counter is /click/ route)"
                )

    await db.commit()
    return {"status": "success", "event_id": event_id, "type": event_type}
