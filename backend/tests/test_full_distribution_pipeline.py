import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distribution import DistributionJob, DistributionJobStatus
from app.models.editorial import EditorialDraft, PublicationRecord
from app.models.event import EventCategory, EventEnvelope, EventSubjectType
from app.models.recipient import Audience, ResolvedAudienceSnapshot, Subscriber, SubscriberContact, Subscription
from app.models.workspace import Workspace
from app.services.audience_resolver import AudienceResolver
from app.services.distribution_service import DistributionExecutor, DistributionPlanner


@pytest.mark.asyncio
async def test_full_distribution_pipeline(db_session: AsyncSession):
    # Setup Data
    workspace = Workspace(name="Test Workspace", owner_type="USER", owner_id="user_123")
    db_session.add(workspace)
    await db_session.flush()

    draft = EditorialDraft(workspace_id=workspace.id, title="Test Draft", content="Content", status="PUBLISHED", artifact_type="ARTICLE")
    db_session.add(draft)
    await db_session.flush()

    # Publication Record
    pub_record = PublicationRecord(article_id="art_123", published_by="user_123")
    db_session.add(pub_record)
    await db_session.flush()

    # Recipient Data
    audience = Audience(name="Test Audience")
    db_session.add(audience)
    await db_session.flush()

    subscriber = Subscriber(primary_email="test@example.com", status="ACTIVE")
    db_session.add(subscriber)
    await db_session.flush()

    subscription = Subscription(subscriber_id=subscriber.id, audience_id=audience.id, status="ACTIVE")
    db_session.add(subscription)

    contact = SubscriberContact(subscriber_id=subscriber.id, type="EMAIL", value="test@example.com", verification_status="VERIFIED")
    db_session.add(contact)
    await db_session.flush()

    # 1. Resolve Audience
    resolver = AudienceResolver(db_session)
    resolved_audience = await resolver.resolve(audience.id)
    assert resolved_audience.total_count == 1
    assert resolved_audience.checksum is not None

    snapshot_id = resolved_audience.snapshot_id
    assert snapshot_id is not None

    snapshot_stmt = select(ResolvedAudienceSnapshot).where(ResolvedAudienceSnapshot.id == snapshot_id)
    snapshot = (await db_session.execute(snapshot_stmt)).scalars().first()
    assert snapshot is not None
    assert snapshot.recipient_count == 1

    # 2. Planner
    planner = DistributionPlanner(db_session)
    manifest = await planner.plan_distribution(
        publication_record_id=pub_record.id,
        subject_type="ARTICLE",
        subject_id=str(draft.id),
        subject_data={"title": draft.title, "content": draft.content, "recipient_email": "test@example.com"},
        audience_snapshot=snapshot.contacts,
        content_checksum="abc"
    )

    assert manifest.id is not None
    assert "email" in manifest.channels
    assert manifest.content_checksum == "abc"

    # Jobs created
    jobs_stmt = select(DistributionJob).where(DistributionJob.manifest_id == manifest.id)
    jobs = (await db_session.execute(jobs_stmt)).scalars().all()
    assert len(jobs) > 0

    email_job = next(j for j in jobs if j.channel == "email")
    assert email_job.status == DistributionJobStatus.QUEUED

    # 3. Executor
    executor = DistributionExecutor(db_session)
    report = await executor.execute_job(email_job.id)

    assert report.status == DistributionJobStatus.SUCCEEDED
    assert report.provider_response is not None

    # Check job status
    await db_session.refresh(email_job)
    assert email_job.status == DistributionJobStatus.SUCCEEDED

    # 4. Delivery Events (simulate async events from ESP)
    event1 = EventEnvelope(
        category=EventCategory.DISTRIBUTION,
        event_type="DELIVERED",
        subject_type=EventSubjectType.DISTRIBUTION_JOB,
        subject_id=str(email_job.id),
        provider="SENDGRID",
        occurred_at=email_job.created_at
    )
    event2 = EventEnvelope(
        category=EventCategory.ANALYTICS,
        event_type="OPENED",
        subject_type=EventSubjectType.DISTRIBUTION_JOB,
        subject_id=str(email_job.id),
        provider="SENDGRID",
        occurred_at=email_job.created_at
    )
    db_session.add_all([event1, event2])
    await db_session.flush()

    events_stmt = select(EventEnvelope).where(EventEnvelope.subject_id == str(email_job.id))
    events = (await db_session.execute(events_stmt)).scalars().all()
    assert len(events) == 2
