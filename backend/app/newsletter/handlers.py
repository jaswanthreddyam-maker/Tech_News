import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.newsletter.repository import NewsletterRepository
from app.newsletter.metrics import tnt_newsletter_subscribe_total
from app.models.telemetry import TimelineNode
from app.newsletter.delivery_tasks import send_confirmation_email

async def handle_newsletter_subscription_created(db: AsyncSession, payload: dict, event_id: int | None = None, is_replay: bool = False):
    """
    Handles NewsletterSubscriptionCreated from the EventOutbox.
    Updates the read model, emits timeline node, and updates metrics.
    Idempotent by tracking last_processed_event_id in the read model.
    """
    repo = NewsletterRepository(db)
    
    # 0. Idempotency Check via Projection
    if event_id is not None:
        stats = await repo.get_stats()
        if stats.last_processed_event_id and stats.last_processed_event_id >= event_id:
            # Already processed
            return

    email = payload.get("email", "unknown")
    subscription_type = payload.get("subscription_type", "DAILY_AI_BRIEFING")
    
    # 1. Write Timeline Node (Only if not a replay, to prevent audit duplication)
    if not is_replay:
        email_hash = hashlib.sha256(email.lower().strip().encode()).hexdigest()
        node = TimelineNode(
            event_type="NEWSLETTER_SUBSCRIPTION_CREATED",
            timestamp=payload.get("timestamp"),
            source="NewsletterService",
            severity="INFO",
            metadata_json={
                "subscriber_id": payload.get("subscriber_id"),
                "email_hash": email_hash,
                "subscription_type": subscription_type,
                "outbox_event_id": event_id
            }
        )
        db.add(node)
    
    # 2. Update Projection (Read Model)
    await repo.increment_stats(total=1, pending=1, event_id=event_id)
    
    # 3. Update Metrics & Enqueue Side-Effects (Only if not a replay, to prevent metric inflation)
    if not is_replay:
        tnt_newsletter_subscribe_total.labels(source=subscription_type).inc()
        
        # Enqueue the confirmation email task
        subscriber_id = payload.get("subscriber_id")
        if subscriber_id:
            send_confirmation_email.delay(subscriber_id)
    
    # Flush all changes
    await db.flush()

async def handle_briefing_approved(db: AsyncSession, payload: dict, event_id: int | None = None, is_replay: bool = False):
    """
    Creates a NewsletterCampaign and EmailDeliveryRecords for all CONFIRMED subscribers NOT in SuppressedEmail.
    """
    from sqlalchemy import select
    from app.newsletter.models import NewsletterCampaign, NewsletterSubscriber, SubscriptionStatus, SuppressedEmail, EmailDeliveryRecord, CampaignAnalyticsProjection
    from app.newsletter.events import EmailCampaignCreated
    from app.core.events.models import EventOutbox
    from datetime import datetime, timezone
    
    briefing_id = payload.get("briefing_id")
    scheduled_at_str = payload.get("scheduled_at")
    scheduled_at = datetime.fromisoformat(scheduled_at_str) if scheduled_at_str else None
    
    # Idempotency / Replay Safety
    existing = await db.execute(select(NewsletterCampaign).where(NewsletterCampaign.briefing_id == briefing_id))
    if existing.scalar_one_or_none():
        return
    
    # Create Campaign
    campaign = NewsletterCampaign(
        briefing_id=briefing_id,
        campaign_name=f"Daily AI Briefing - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        status="SCHEDULED",
        scheduled_at=scheduled_at
    )
    db.add(campaign)
    await db.flush()
    
    # Initialize projection
    projection = CampaignAnalyticsProjection(campaign_id=campaign.id)
    db.add(projection)

    # Get eligible subscribers
    stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.status == SubscriptionStatus.CONFIRMED)
    result = await db.execute(stmt)
    subscribers = result.scalars().all()
    
    # Get suppressions
    supp_stmt = select(SuppressedEmail.email)
    supp_result = await db.execute(supp_stmt)
    suppressed_emails = set(supp_result.scalars().all())

    eligible_count = 0
    for sub in subscribers:
        if sub.email not in suppressed_emails:
            db.add(EmailDeliveryRecord(
                campaign_id=campaign.id,
                subscriber_id=sub.id,
                status="PENDING"
            ))
            eligible_count += 1
            
    projection.total_recipients = eligible_count
    await db.flush()
    
    # Emit Campaign Created
    event_payload = EmailCampaignCreated(
        campaign_id=campaign.id,
        briefing_id=briefing_id,
        campaign_name=campaign.campaign_name,
        timestamp=datetime.now(timezone.utc).isoformat()
    ).model_dump()
    db.add(EventOutbox(event_type="EmailCampaignCreated", payload=event_payload))

async def handle_email_campaign_created(db: AsyncSession, payload: dict, event_id: int | None = None, is_replay: bool = False):
    """
    Enqueues dispatch_email_to_subscriber for each pending delivery.
    """
    from sqlalchemy import select
    from app.newsletter.models import EmailDeliveryRecord
    from app.newsletter.campaign_tasks import dispatch_email_to_subscriber
    
    campaign_id = payload.get("campaign_id")
    stmt = select(EmailDeliveryRecord).where(
        EmailDeliveryRecord.campaign_id == campaign_id,
        EmailDeliveryRecord.status == "PENDING"
    )
    result = await db.execute(stmt)
    deliveries = result.scalars().all()
    
    for d in deliveries:
        d.status = "QUEUED"
        if not is_replay:
            dispatch_email_to_subscriber.delay(campaign_id, d.subscriber_id)
            
async def handle_email_delivery_event(db: AsyncSession, event_type: str, payload: dict, event_id: int | None = None, is_replay: bool = False):
    """
    Handles EmailSent, EmailOpened, LinkClicked, EmailBounced
    Updates the DeliveryRecord and the AnalyticsProjection.
    """
    from sqlalchemy import select
    from app.newsletter.models import EmailDeliveryRecord, CampaignAnalyticsProjection, SuppressedEmail, NewsletterSubscriber, SubscriptionStatus
    from datetime import datetime, timezone
    
    delivery_id = payload.get("delivery_id")
    campaign_id = payload.get("campaign_id")
    subscriber_id = payload.get("subscriber_id")
    
    # Resolve missing IDs for pixel loads
    if not subscriber_id and delivery_id:
        stmt = select(EmailDeliveryRecord).where(EmailDeliveryRecord.id == delivery_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            campaign_id = record.campaign_id
            subscriber_id = record.subscriber_id
        else:
            return # Cannot resolve

    record = None
    if campaign_id and subscriber_id:
        stmt = select(EmailDeliveryRecord).where(EmailDeliveryRecord.campaign_id == campaign_id, EmailDeliveryRecord.subscriber_id == subscriber_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        
    proj_stmt = select(CampaignAnalyticsProjection).where(CampaignAnalyticsProjection.campaign_id == campaign_id)
    proj_result = await db.execute(proj_stmt)
    projection = proj_result.scalar_one_or_none()

    if event_type == "EmailSent":
        if record:
            record.status = "SENT"
            record.sent_at = datetime.fromisoformat(payload.get("timestamp"))
        if projection: projection.sent_count += 1
            
    elif event_type == "EmailOpened":
        if record and record.status != "OPENED":
            record.status = "OPENED"
            record.opened_at = datetime.fromisoformat(payload.get("timestamp"))
        if projection: projection.opened_count += 1
            
    elif event_type == "LinkClicked":
        if record and record.status != "CLICKED":
            record.status = "CLICKED"
        if projection: projection.clicked_count += 1
            
    elif event_type == "EmailBounced":
        email = payload.get("email")
        # Add to suppression list
        db.add(SuppressedEmail(email=email, reason=payload.get("reason")))
        
        # Mark unsubscribed
        sub_stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
        sub_result = await db.execute(sub_stmt)
        subscriber = sub_result.scalar_one_or_none()
        if subscriber:
            subscriber.status = SubscriptionStatus.UNSUBSCRIBED
            
        if record:
            record.status = "BOUNCED"
            record.bounced_at = datetime.fromisoformat(payload.get("timestamp"))
        if projection: projection.bounced_count += 1

    # Recalculate Projection Rates
    if projection and projection.total_recipients > 0:
        projection.delivery_rate = f"{(projection.sent_count / projection.total_recipients * 100):.2f}"
        if projection.sent_count > 0:
            projection.open_rate = f"{(projection.opened_count / projection.sent_count * 100):.2f}"
            projection.click_rate = f"{(projection.clicked_count / projection.sent_count * 100):.2f}"
            projection.bounce_rate = f"{(projection.bounced_count / projection.sent_count * 100):.2f}"
