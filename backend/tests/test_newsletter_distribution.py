import pytest
from sqlalchemy import select

from app.models.distribution import DistributionJob, DistributionJobStatus
from app.models.editorial import EditorialDraft, EditorialDraftStatus, PublicationRecord
from app.models.recipient import Audience, Subscriber, SubscriberContact, Subscription
from app.models.workspace import Workspace
from app.services.distribution_service import DistributionExecutor, DistributionPlanner


@pytest.mark.asyncio
async def test_newsletter_distribution_flow(db_session):
    workspace = Workspace(name="TNT Newsroom", owner_type="SYSTEM", owner_id="sys_1")
    db_session.add(workspace)
    await db_session.flush()

    # 1. Setup Audience with a Verified Subscriber
    audience = Audience(name="Daily Tech Newsletter")
    db_session.add(audience)
    await db_session.flush()

    sub = Subscriber(primary_email="newsletter@example.com", status="ACTIVE")
    db_session.add(sub)
    await db_session.flush()

    contact = SubscriberContact(
        subscriber_id=sub.id,
        type="EMAIL",
        value="newsletter@example.com",
        is_primary=True,
        verification_status="VERIFIED"
    )
    db_session.add(contact)

    subscription = Subscription(
        subscriber_id=sub.id,
        audience_id=audience.id,
        status="ACTIVE"
    )
    db_session.add(subscription)
    await db_session.commit()

    # 2. Create EditorialDraft as a NEWSLETTER
    draft = EditorialDraft(
        workspace_id=workspace.id,
        artifact_type="NEWSLETTER",
        title="Welcome to Phase 12",
        content="This is the new email digest.",
        status=EditorialDraftStatus.PUBLISHED.value
    )
    db_session.add(draft)
    await db_session.flush()

    # 3. Create PublicationRecord (Mocking the publishing pipeline)
    pub = PublicationRecord(
        article_id=f"newsletter_{draft.id}",
        published_by="system",
    )
    db_session.add(pub)
    await db_session.commit()

    # 4. Distribution Planner resolves capability based on artifact_type
    planner = DistributionPlanner(db_session)
    manifest = await planner.plan_distribution(
        publication_record_id=pub.id,
        subject_type=draft.artifact_type,
        subject_id=str(draft.id),
        subject_data={
            "subject": draft.title,
            "html": draft.content,
            "text": draft.content,
            "recipient_email": "newsletter@example.com" # Mock resolved from AudienceResolver
        }
    )

    assert manifest is not None
    assert manifest.publication_record_id == pub.id

    # 5. Verify the job was created for EmailCapability
    stmt = select(DistributionJob).where(DistributionJob.manifest_id == manifest.id)
    res = await db_session.execute(stmt)
    jobs = res.scalars().all()

    # We expect 1 job for the email channel because we passed NEWSLETTER subject_type
    email_jobs = [j for j in jobs if j.channel == "email"]
    assert len(email_jobs) == 1

    job = email_jobs[0]
    assert job.status == DistributionJobStatus.QUEUED

    # 6. Execute Job
    executor = DistributionExecutor(db_session)
    report = await executor.execute_job(job.id)

    # Validate lifecycle
    assert report.status == DistributionJobStatus.SUCCEEDED
    assert report.provider_response["message_id"] == f"msg_{job.id}"

    # Reload job
    await db_session.refresh(job)
    assert job.status == DistributionJobStatus.SUCCEEDED
