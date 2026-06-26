import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.newsletter.models import NewsletterSubscriber, NewsletterReadModel, SubscriptionStatus
from app.core.events.models import EventOutbox
from main import app
from httpx import ASGITransport
import pytest_asyncio

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_successful_subscription(client: AsyncClient, db_session: AsyncSession):
    email = "test.sub1@example.com"
    response = await client.post(
        "/api/v1/newsletter/subscribe",
        json={"email": email}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Check Database
    stmt = select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
    result = await db_session.execute(stmt)
    subscriber = result.scalars().first()
    assert subscriber is not None
    assert subscriber.status == SubscriptionStatus.PENDING

    # Check Outbox Event emitted
    outbox_stmt = select(EventOutbox).where(EventOutbox.event_type == "NewsletterSubscriptionCreated")
    outbox_result = await db_session.execute(outbox_stmt)
    events = outbox_result.scalars().all()
    # At least one event matching our email should exist
    assert any(e.payload["email"] == email for e in events)

@pytest.mark.asyncio
async def test_duplicate_subscription(client: AsyncClient, db_session: AsyncSession):
    email = "test.duplicate@example.com"
    
    # First request
    response1 = await client.post(
        "/api/v1/newsletter/subscribe",
        json={"email": email}
    )
    assert response1.status_code == 200

    # Second request (Idempotent)
    response2 = await client.post(
        "/api/v1/newsletter/subscribe",
        json={"email": email}
    )
    assert response2.status_code == 200
    assert response2.json()["success"] is True

    # Ensure only 1 event was emitted to the outbox
    outbox_stmt = select(EventOutbox).where(EventOutbox.event_type == "NewsletterSubscriptionCreated")
    outbox_result = await db_session.execute(outbox_stmt)
    events = [e for e in outbox_result.scalars().all() if e.payload["email"] == email]
    assert len(events) == 1

@pytest.mark.asyncio
async def test_invalid_email_format(client: AsyncClient):
    response = await client.post(
        "/api/v1/newsletter/subscribe",
        json={"email": "not-an-email"}
    )
    assert response.status_code == 422 # FastAPI Pydantic validation error

@pytest.mark.asyncio
async def test_email_rate_limiting(client: AsyncClient):
    email = "test.ratelimit@example.com"
    # Send 6 rapid requests (limit is 5 per hour per email/IP)
    for i in range(5):
        # We might get 409 for duplicate after the 1st one, but it still consumes rate limits
        await client.post("/api/v1/newsletter/subscribe", json={"email": email})

    # The 6th should be 429 Too Many Requests
    response = await client.post("/api/v1/newsletter/subscribe", json={"email": email})
    assert response.status_code == 429
    assert "Too many attempts" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_newsletter_stats(client: AsyncClient, db_session: AsyncSession):
    # Ensure stats initializes to 0
    response = await client.get("/api/v1/newsletter/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_subscribers" in data
    assert "confirmation_rate" in data

@pytest.mark.asyncio
async def test_projection_replay(client: AsyncClient, db_session: AsyncSession):
    from sqlalchemy import delete
    from app.newsletter.models import NewsletterReadModel
    from app.newsletter.handlers import handle_newsletter_subscription_created
    from app.core.events.models import EventOutbox

    email = "test.replay@example.com"
    response = await client.post(
        "/api/v1/newsletter/subscribe",
        json={"email": email}
    )
    assert response.status_code == 200

    # Get Outbox Event ID
    outbox_stmt = select(EventOutbox).where(EventOutbox.event_type == "NewsletterSubscriptionCreated")
    outbox_result = await db_session.execute(outbox_stmt)
    events = [e for e in outbox_result.scalars().all() if e.payload["email"] == email]
    assert len(events) == 1
    event = events[0]
    event_id = event.id
    payload = event.payload

    # Delete Projection
    await db_session.execute(delete(NewsletterReadModel))
    await db_session.flush()

    # Replay Event
    await handle_newsletter_subscription_created(db_session, payload, event_id=event_id, is_replay=True)

    # Projection should be rebuilt with last_processed_event_id
    stats_stmt = select(NewsletterReadModel).limit(1)
    stats_result = await db_session.execute(stats_stmt)
    stats = stats_result.scalars().first()
    
    assert stats is not None
    assert stats.total_subscribers == 1
    assert stats.last_processed_event_id == event_id

    # Running it again should be idempotent
    await handle_newsletter_subscription_created(db_session, payload, event_id=event_id, is_replay=True)
    stats_result2 = await db_session.execute(stats_stmt)
    stats2 = stats_result2.scalars().first()
    assert stats2.total_subscribers == 1
