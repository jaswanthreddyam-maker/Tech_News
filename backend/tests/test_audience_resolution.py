import pytest

from app.models.recipient import Audience, Subscriber, SubscriberContact, Subscription
from app.services.audience_resolver import AudienceResolver


@pytest.mark.asyncio
async def test_audience_resolution(db_session):
    # Setup
    aud = Audience(name="Test Audience")
    db_session.add(aud)
    await db_session.flush()

    # Sub 1: Verified Email
    sub1 = Subscriber(primary_email="v1@example.com", status="ACTIVE")
    db_session.add(sub1)
    await db_session.flush()
    db_session.add(SubscriberContact(
        subscriber_id=sub1.id, type="EMAIL", value="v1@example.com", verification_status="VERIFIED"
    ))
    db_session.add(Subscription(subscriber_id=sub1.id, audience_id=aud.id, status="ACTIVE"))

    # Sub 2: Unverified Email
    sub2 = Subscriber(primary_email="u2@example.com", status="ACTIVE")
    db_session.add(sub2)
    await db_session.flush()
    db_session.add(SubscriberContact(
        subscriber_id=sub2.id, type="EMAIL", value="u2@example.com", verification_status="UNVERIFIED"
    ))
    db_session.add(Subscription(subscriber_id=sub2.id, audience_id=aud.id, status="ACTIVE"))

    # Sub 3: Verified, but unsubscribed
    sub3 = Subscriber(primary_email="v3@example.com", status="ACTIVE")
    db_session.add(sub3)
    await db_session.flush()
    db_session.add(SubscriberContact(
        subscriber_id=sub3.id, type="EMAIL", value="v3@example.com", verification_status="VERIFIED"
    ))
    db_session.add(Subscription(subscriber_id=sub3.id, audience_id=aud.id, status="UNSUBSCRIBED"))

    await db_session.commit()

    # Test Resolver
    resolver = AudienceResolver(db_session)
    resolved = await resolver.resolve(aud.id)

    assert resolved.audience_id == aud.id
    assert resolved.total_count == 1
    assert len(resolved.resolved_contacts) == 1
    assert resolved.resolved_contacts[0].subscriber_id == sub1.id
    assert resolved.resolved_contacts[0].verification_status == "VERIFIED"
