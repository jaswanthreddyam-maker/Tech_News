import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipient import (
    Audience,
    DeliveryPreference,
    Preference,
    Segment,
    Subscriber,
    SubscriberContact,
    Subscription,
    SubscriptionEvent,
)

logger = logging.getLogger(__name__)

class SubscriberService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_subscriber(self, primary_email: str, display_name: str | None = None, user_id: str | None = None) -> Subscriber:
        stmt = select(Subscriber).where(Subscriber.primary_email == primary_email)
        res = await self.db.execute(stmt)
        subscriber = res.scalars().first()

        if not subscriber:
            subscriber = Subscriber(
                primary_email=primary_email,
                display_name=display_name,
                user_id=user_id,
                status="ACTIVE"
            )
            self.db.add(subscriber)
            await self.db.flush()

            # Automatically add an email contact
            contact = SubscriberContact(
                subscriber_id=subscriber.id,
                type="EMAIL",
                value=primary_email,
                is_primary=True,
                verification_status="UNVERIFIED"
            )
            self.db.add(contact)
            await self._log_event(subscriber.id, "SUBSCRIBER_CREATED", {"email": primary_email})
            await self.db.commit()

        return subscriber

    async def add_contact(self, subscriber_id: int, contact_type: str, value: str, is_primary: bool = False) -> SubscriberContact:
        contact = SubscriberContact(
            subscriber_id=subscriber_id,
            type=contact_type,
            value=value,
            is_primary=is_primary,
            verification_status="UNVERIFIED"
        )
        self.db.add(contact)
        await self._log_event(subscriber_id, "CONTACT_ADDED", {"type": contact_type, "value": value})
        await self.db.commit()
        return contact

    async def subscribe_to_audience(self, subscriber_id: int, audience_id: int) -> Subscription:
        stmt = select(Subscription).where(
            Subscription.subscriber_id == subscriber_id,
            Subscription.audience_id == audience_id
        )
        res = await self.db.execute(stmt)
        subscription = res.scalars().first()

        if subscription:
            if subscription.status != "ACTIVE":
                subscription.status = "ACTIVE"
                await self._log_event(subscriber_id, "RESUBSCRIBED", {"audience_id": audience_id})
                await self.db.commit()
            return subscription

        subscription = Subscription(
            subscriber_id=subscriber_id,
            audience_id=audience_id,
            status="ACTIVE"
        )
        self.db.add(subscription)
        await self._log_event(subscriber_id, "SUBSCRIBED", {"audience_id": audience_id})
        await self.db.commit()
        return subscription

    async def set_preference(self, subscriber_id: int, subject_type: str, subject_id: str, preference_val: str, weight: float = 1.0) -> Preference:
        stmt = select(Preference).where(
            Preference.subscriber_id == subscriber_id,
            Preference.subject_type == subject_type,
            Preference.subject_id == subject_id
        )
        res = await self.db.execute(stmt)
        pref = res.scalars().first()

        if pref:
            pref.preference = preference_val
            pref.weight = weight
        else:
            pref = Preference(
                subscriber_id=subscriber_id,
                subject_type=subject_type,
                subject_id=subject_id,
                preference=preference_val,
                weight=weight
            )
            self.db.add(pref)

        await self._log_event(subscriber_id, "CHANGED_PREFERENCE", {"subject_type": subject_type, "subject_id": subject_id, "preference": preference_val})
        await self.db.commit()
        return pref

    async def set_delivery_preference(self, subscriber_id: int, channel: str, enabled: bool, quiet_hours: str | None = None, timezone: str | None = None) -> DeliveryPreference:
        stmt = select(DeliveryPreference).where(
            DeliveryPreference.subscriber_id == subscriber_id,
            DeliveryPreference.channel == channel
        )
        res = await self.db.execute(stmt)
        pref = res.scalars().first()

        if pref:
            pref.enabled = enabled
            pref.quiet_hours = quiet_hours
            pref.timezone = timezone
        else:
            pref = DeliveryPreference(
                subscriber_id=subscriber_id,
                channel=channel,
                enabled=enabled,
                quiet_hours=quiet_hours,
                timezone=timezone
            )
            self.db.add(pref)

        await self._log_event(subscriber_id, "CHANGED_DELIVERY_PREF", {"channel": channel, "enabled": enabled})
        await self.db.commit()
        return pref

    async def _log_event(self, subscriber_id: int, event: str, metadata: dict[str, Any]):
        sub_event = SubscriptionEvent(
            subscriber_id=subscriber_id,
            event=event,
            metadata_info=metadata,
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(sub_event)

class AudienceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_audience(self, name: str, description: str | None = None) -> Audience:
        audience = Audience(name=name, description=description)
        self.db.add(audience)
        await self.db.commit()
        return audience

    async def create_segment(self, audience_id: int, name: str, expression: str, compiled_expression: dict | None = None) -> Segment:
        segment = Segment(
            audience_id=audience_id,
            name=name,
            expression=expression,
            compiled_expression=compiled_expression
        )
        self.db.add(segment)
        await self.db.commit()
        return segment
