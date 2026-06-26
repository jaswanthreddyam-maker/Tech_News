import pytest
from sqlalchemy import select

from app.models.recipient import (
    SubscriberContact,
    SubscriptionEvent,
)
from app.services.recipient_service import AudienceService, SubscriberService


@pytest.mark.asyncio
async def test_recipient_infrastructure(db_session):
    # 1. Create a subscriber using the service
    sub_service = SubscriberService(db_session)
    aud_service = AudienceService(db_session)

    subscriber = await sub_service.get_or_create_subscriber(
        primary_email="john@example.com",
        display_name="John Doe",
        user_id="user_123"
    )

    assert subscriber.id is not None
    assert subscriber.primary_email == "john@example.com"

    # Verify primary contact was automatically created
    stmt = select(SubscriberContact).where(SubscriberContact.subscriber_id == subscriber.id)
    res = await db_session.execute(stmt)
    contacts = res.scalars().all()
    assert len(contacts) == 1
    assert contacts[0].type == "EMAIL"
    assert contacts[0].value == "john@example.com"

    # 2. Add an additional contact (Push token)
    push_contact = await sub_service.add_contact(
        subscriber_id=subscriber.id,
        contact_type="DEVICE_TOKEN",
        value="firebase_token_abc123"
    )
    assert push_contact.id is not None
    assert push_contact.type == "DEVICE_TOKEN"

    # 3. Create an Audience
    audience = await aud_service.create_audience(name="Weekly Newsletter", description="Weekly updates")
    assert audience.id is not None

    # 4. Subscribe the user to the Audience
    subscription = await sub_service.subscribe_to_audience(subscriber.id, audience.id)
    assert subscription.status == "ACTIVE"

    # 5. Set Preferences (Subject-based)
    pref = await sub_service.set_preference(
        subscriber_id=subscriber.id,
        subject_type="TOPIC",
        subject_id="AI",
        preference_val="FOLLOW"
    )
    assert pref.subject_type == "TOPIC"
    assert pref.subject_id == "AI"

    # 6. Set Delivery Preferences
    delivery_pref = await sub_service.set_delivery_preference(
        subscriber_id=subscriber.id,
        channel="Push",
        enabled=True,
        quiet_hours="22:00-08:00",
        timezone="Asia/Kolkata"
    )
    assert delivery_pref.quiet_hours == "22:00-08:00"

    # 7. Verify Events log
    stmt = select(SubscriptionEvent).where(SubscriptionEvent.subscriber_id == subscriber.id).order_by(SubscriptionEvent.timestamp.asc())
    res = await db_session.execute(stmt)
    events = res.scalars().all()

    # Expected events: SUBSCRIBER_CREATED, CONTACT_ADDED, SUBSCRIBED, CHANGED_PREFERENCE, CHANGED_DELIVERY_PREF
    event_names = [e.event for e in events]
    assert "SUBSCRIBER_CREATED" in event_names
    assert "CONTACT_ADDED" in event_names
    assert "SUBSCRIBED" in event_names
    assert "CHANGED_PREFERENCE" in event_names
    assert "CHANGED_DELIVERY_PREF" in event_names
