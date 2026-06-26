from celery import shared_task
import logging
from datetime import datetime, timezone
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import SessionLocal
from app.newsletter.models import NewsletterBriefing, NewsletterBriefingVersion, NewsletterCampaign, NewsletterSubscriber, SubscriptionStatus, SuppressedEmail
from app.newsletter.events import DailyBriefingGenerated, BriefingApproved, EmailCampaignCreated, EmailDispatchRequested
from app.core.events.models import EventOutbox
from app.newsletter.briefing_generator import get_briefing_generator
from sqlalchemy import update

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def generate_daily_briefing(self):
    """
    Triggered by Celery Beat every morning.
    Generates the briefing, persists it, and emits DailyBriefingGenerated.
    """
    logger.info("Task generate_daily_briefing started.")
    db = SessionLocal()
    
    try:
        # Generate the content
        generator = get_briefing_generator()
        content = asyncio.run(generator.generate_briefing())
        
        # Persist the briefing
        briefing = NewsletterBriefing(
            status="DRAFT"
        )
        db.add(briefing)
        db.flush() # Sync flush to get ID
        
        # Persist the v1 version
        version = NewsletterBriefingVersion(
            briefing_id=briefing.id,
            version_number=1,
            title=content["title"],
            content_html=content["content_html"],
            content_text=content["content_text"],
            created_by="ai-generator",
            source="AI_GENERATED"
        )
        db.add(version)
        db.flush()
        
        # Link current version
        briefing.current_version_id = version.id
        db.flush()
        
        # Emit Domain Event
        event_payload = DailyBriefingGenerated(
            briefing_id=briefing.id,
            title=version.title,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).model_dump()
        db.add(EventOutbox(event_type="DailyBriefingGenerated", payload=event_payload))
        
        db.commit()
        logger.info(f"Daily briefing {briefing.id} (v1) generated and saved as DRAFT.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to generate daily briefing: {e}")
        raise e
    finally:
        db.close()

@shared_task(bind=True)
def dispatch_email_to_subscriber(self, campaign_id: int, subscriber_id: int):
    """
    Actually sends the email using the EmailProvider.
    In a real implementation, this handles injecting tracking URLs.
    (This is typically enqueue via an event handler)
    """
    from app.core.email.email_service import get_email_provider
    from app.newsletter.models import EmailDeliveryRecord, EmailDeliveryStatus
    from app.newsletter.events import EmailSent
    
    db = SessionLocal()
    try:
        campaign = db.query(NewsletterCampaign).get(campaign_id)
        briefing = db.query(NewsletterBriefing).get(campaign.briefing_id)
        version = db.query(NewsletterBriefingVersion).get(briefing.current_version_id)
        subscriber = db.query(NewsletterSubscriber).get(subscriber_id)
        
        if not all([campaign, briefing, version, subscriber]):
            logger.error("Missing campaign, briefing, version, or subscriber.")
            return

        # Atomic row lock for retry safety
        stmt = (
            update(EmailDeliveryRecord)
            .where(
                EmailDeliveryRecord.campaign_id == campaign_id,
                EmailDeliveryRecord.subscriber_id == subscriber_id,
                EmailDeliveryRecord.status == "QUEUED"
            )
            .values(status="SENDING")
        )
        result = db.execute(stmt)
        if result.rowcount == 0:
            logger.info(f"Delivery {campaign_id}-{subscriber_id} not in QUEUED state. Skipping dispatch.")
            return
        db.commit() # Commit the lock
        
        # Inject tracking links
        base_url = "http://localhost:8000"
        delivery_id = f"{campaign_id}{subscriber_id}" # Simplified delivery ID
        track_open_url = f"{base_url}/api/v1/newsletter/track/open/{delivery_id}.gif"
        unsubscribe_url = f"{base_url}/api/v1/newsletter/unsubscribe/{subscriber.unsubscribe_token}"

        # Note: HTML manipulation should ideally use BeautifulSoup or similar, 
        # but for v1 MVP we just append it.
        html_content = version.content_html.replace(
            "<!-- Tracking Pixel and Unsubscribe links will be injected by the delivery task -->",
            f'<img src="{track_open_url}" width="1" height="1" /><br><a href="{unsubscribe_url}">Unsubscribe</a>'
        )

        provider = get_email_provider()
        provider_msg_id = asyncio.run(provider.send_email(
            to_email=subscriber.email,
            subject=campaign.campaign_name,
            html_content=html_content,
            text_content=version.content_text,
            campaign_id=campaign.id,
            subscriber_id=subscriber.id
        ))

        # Update delivery status
        delivery_record = db.query(EmailDeliveryRecord).filter_by(campaign_id=campaign_id, subscriber_id=subscriber_id).first()
        if delivery_record:
            delivery_record.status = EmailDeliveryStatus.SENT
            delivery_record.provider_message_id = provider_msg_id
            delivery_record.sent_at = datetime.now(timezone.utc)
            
            # Emit EmailSent
            sent_payload = EmailSent(
                campaign_id=campaign_id,
                subscriber_id=subscriber_id,
                delivery_id=delivery_record.id,
                provider_message_id=provider_msg_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            ).model_dump()
            db.add(EventOutbox(event_type="EmailSent", payload=sent_payload))
            
            db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to dispatch email: {e}")
        self.retry(exc=e, countdown=60)
    finally:
        db.close()
