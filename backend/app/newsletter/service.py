import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.newsletter.repository import NewsletterRepository
from app.newsletter.models import NewsletterSubscriber, SubscriptionStatus
from app.newsletter.events import (
    NewsletterSubscriptionCreated, NewsletterSubscriptionConfirmed, NewsletterUnsubscribed,
    EmailOpened, LinkClicked, EmailBounced
)
from app.core.events.models import EventOutbox

class NewsletterService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = NewsletterRepository(session)

    async def subscribe(self, email: str, subscription_type: str = "DAILY_AI_BRIEFING") -> NewsletterSubscriber:
        # Check uniqueness
        existing = await self.repository.get_by_email(email)
        if existing:
            if existing.status == SubscriptionStatus.UNSUBSCRIBED:
                # Re-subscribe flow
                existing.status = SubscriptionStatus.PENDING
                existing.subscription_type = subscription_type
                existing.unsubscribe_token = str(uuid.uuid4())
                existing.confirmation_token = str(uuid.uuid4())
                subscriber = existing
            else:
                # IDEMPOTENT: already pending or confirmed, just return without emitting duplicate events
                return existing
        else:
            # Create new subscriber
            subscriber = NewsletterSubscriber(
                email=email,
                subscription_type=subscription_type,
                unsubscribe_token=str(uuid.uuid4()),
                confirmation_token=str(uuid.uuid4())
            )
            self.session.add(subscriber)
        
        # Flush to get the ID
        await self.session.flush()

        # Create Domain Event Payload
        event_payload = NewsletterSubscriptionCreated(
            subscriber_id=subscriber.id,
            email=subscriber.email,
            subscription_type=subscriber.subscription_type,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).model_dump()

        # Emit to Outbox (Transactional Outbox Pattern)
        outbox_event = EventOutbox(
            event_type="NewsletterSubscriptionCreated",
            payload=event_payload
        )
        self.session.add(outbox_event)

        # The session commit will be handled by the caller (API dependency)
        return subscriber

    async def confirm_subscription(self, token: str) -> bool:
        stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.confirmation_token == token)
        result = await self.session.execute(stmt)
        subscriber = result.scalar_one_or_none()
        
        if not subscriber:
            return False
            
        if subscriber.status != SubscriptionStatus.CONFIRMED:
            subscriber.status = SubscriptionStatus.CONFIRMED
            subscriber.confirmed_at = datetime.now(timezone.utc)
            
            event_payload = NewsletterSubscriptionConfirmed(
                subscriber_id=subscriber.id,
                email=subscriber.email,
                timestamp=datetime.now(timezone.utc).isoformat()
            ).model_dump()
            
            self.session.add(EventOutbox(event_type="NewsletterSubscriptionConfirmed", payload=event_payload))
            await self.session.flush()
        return True

    async def unsubscribe(self, token: str) -> bool:
        stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.unsubscribe_token == token)
        result = await self.session.execute(stmt)
        subscriber = result.scalar_one_or_none()
        
        if not subscriber:
            return False
            
        if subscriber.status != SubscriptionStatus.UNSUBSCRIBED:
            subscriber.status = SubscriptionStatus.UNSUBSCRIBED
            
            event_payload = NewsletterUnsubscribed(
                subscriber_id=subscriber.id,
                email=subscriber.email,
                timestamp=datetime.now(timezone.utc).isoformat()
            ).model_dump()
            
            self.session.add(EventOutbox(event_type="NewsletterUnsubscribed", payload=event_payload))
            await self.session.flush()
        return True

    async def track_open(self, delivery_id: int):
        # We just emit the event. Handlers will update models to 'OPENED'
        # The pixel loads usually don't have a subscriber_id handy without a join,
        # but the event handler can look it up based on delivery_id.
        event_payload = EmailOpened(
            campaign_id=0, # Will be hydrated by handler
            subscriber_id=0, # Will be hydrated by handler
            delivery_id=delivery_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).model_dump()
        
        self.session.add(EventOutbox(event_type="EmailOpened", payload=event_payload))
        await self.session.flush()

    async def track_click(self, delivery_id: int, url: str):
        event_payload = LinkClicked(
            campaign_id=0, # Hydrated by handler
            subscriber_id=0,
            delivery_id=delivery_id,
            url=url,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).model_dump()
        
        self.session.add(EventOutbox(event_type="LinkClicked", payload=event_payload))
        await self.session.flush()

    async def process_esp_webhook(self, payload: dict):
        # A generic ESP webhook. In Resend, type="email.bounced"
        event_type = payload.get("type", "")
        if event_type == "email.bounced":
            data = payload.get("data", {})
            email = data.get("to", [""])[0] if isinstance(data.get("to"), list) else data.get("to", "")
            
            event_payload = EmailBounced(
                email=email,
                provider_message_id=data.get("email_id", ""),
                reason=data.get("reason", "unknown_bounce"),
                timestamp=datetime.now(timezone.utc).isoformat()
            ).model_dump()
            self.session.add(EventOutbox(event_type="EmailBounced", payload=event_payload))
        await self.session.flush()

    # Editorial Workflow
    
    async def update_briefing(self, briefing_id: int, title: str, content_html: str, content_text: str, editor_id: str) -> dict:
        from app.newsletter.models import NewsletterBriefing, NewsletterBriefingVersion
        from app.newsletter.events import BriefingUpdated
        
        stmt = select(NewsletterBriefing).where(NewsletterBriefing.id == briefing_id)
        result = await self.session.execute(stmt)
        briefing = result.scalar_one_or_none()
        
        if not briefing:
            raise HTTPException(status_code=404, detail="Briefing not found")
        if briefing.status != "DRAFT":
            raise HTTPException(status_code=400, detail="Only DRAFT briefings can be updated")
            
        # Get max version number
        v_stmt = select(NewsletterBriefingVersion).where(NewsletterBriefingVersion.briefing_id == briefing_id).order_by(NewsletterBriefingVersion.version_number.desc())
        v_result = await self.session.execute(v_stmt)
        latest_version = v_result.scalars().first()
        next_version_num = (latest_version.version_number + 1) if latest_version else 1
        
        new_version = NewsletterBriefingVersion(
            briefing_id=briefing.id,
            version_number=next_version_num,
            title=title,
            content_html=content_html,
            content_text=content_text,
            created_by=editor_id,
            source="EDITOR_EDIT"
        )
        self.session.add(new_version)
        await self.session.flush()
        
        briefing.current_version_id = new_version.id
        
        event_payload = BriefingUpdated(
            briefing_id=briefing.id,
            version_id=new_version.id,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).model_dump()
        self.session.add(EventOutbox(event_type="BriefingUpdated", payload=event_payload))
        await self.session.flush()
        
        return {"id": briefing.id, "version": next_version_num}

    async def approve_briefing(self, briefing_id: int, scheduled_at: datetime | None = None) -> bool:
        from app.newsletter.models import NewsletterBriefing
        from app.newsletter.events import BriefingApproved
        
        stmt = select(NewsletterBriefing).where(NewsletterBriefing.id == briefing_id)
        result = await self.session.execute(stmt)
        briefing = result.scalar_one_or_none()
        
        if not briefing or briefing.status != "DRAFT":
            return False
            
        briefing.status = "APPROVED"
        briefing.approved_at = datetime.now(timezone.utc)
        
        event_payload = BriefingApproved(
            briefing_id=briefing.id,
            scheduled_at=scheduled_at.isoformat() if scheduled_at else None,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).model_dump()
        self.session.add(EventOutbox(event_type="BriefingApproved", payload=event_payload))
        await self.session.flush()
        return True

    async def reject_briefing(self, briefing_id: int) -> bool:
        from app.newsletter.models import NewsletterBriefing
        from app.newsletter.events import BriefingRejected
        
        stmt = select(NewsletterBriefing).where(NewsletterBriefing.id == briefing_id)
        result = await self.session.execute(stmt)
        briefing = result.scalar_one_or_none()
        
        if not briefing or briefing.status != "DRAFT":
            return False
            
        briefing.status = "REJECTED"
        
        event_payload = BriefingRejected(
            briefing_id=briefing.id,
            timestamp=datetime.now(timezone.utc).isoformat()
        ).model_dump()
        self.session.add(EventOutbox(event_type="BriefingRejected", payload=event_payload))
        await self.session.flush()
        return True

    async def archive_briefing(self, briefing_id: int) -> bool:
        from app.newsletter.models import NewsletterBriefing
        
        stmt = select(NewsletterBriefing).where(NewsletterBriefing.id == briefing_id)
        result = await self.session.execute(stmt)
        briefing = result.scalar_one_or_none()
        
        if not briefing or briefing.status not in ["APPROVED", "REJECTED"]:
            return False
            
        briefing.status = "ARCHIVED"
        await self.session.flush()
        return True
