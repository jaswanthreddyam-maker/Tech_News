import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.newsletter.models import (
    NewsletterBriefing, NewsletterBriefingVersion, EmailDeliveryRecord, EmailDeliveryStatus
)
from app.core.events.models import EventOutbox
from app.newsletter.service import NewsletterService

@pytest.mark.asyncio
async def test_campaign_unique_constraint(db_session):
    """Ensure database throws integrity error on duplicate campaign+subscriber."""
    delivery1 = EmailDeliveryRecord(campaign_id=1, subscriber_id=1, status=EmailDeliveryStatus.PENDING)
    db_session.add(delivery1)
    await db_session.flush()

    delivery2 = EmailDeliveryRecord(campaign_id=1, subscriber_id=1, status=EmailDeliveryStatus.PENDING)
    db_session.add(delivery2)
    
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_editorial_state_transitions(db_session):
    """Test versions generated during update_briefing."""
    service = NewsletterService(db_session)
    
    # 1. Create initial draft (simulating AI Generation)
    briefing = NewsletterBriefing(status="DRAFT")
    db_session.add(briefing)
    await db_session.flush()
    
    version1 = NewsletterBriefingVersion(
        briefing_id=briefing.id,
        version_number=1,
        title="AI Draft",
        content_html="<p>AI</p>",
        content_text="AI",
        source="AI_GENERATED"
    )
    db_session.add(version1)
    await db_session.flush()
    briefing.current_version_id = version1.id
    await db_session.flush()
    
    # 2. Update via Editor
    result = await service.update_briefing(briefing.id, "Editor Edit", "<p>Editor</p>", "Editor", "editor-1")
    assert result["version"] == 2
    
    # Verify DB state
    stmt = select(NewsletterBriefingVersion).where(NewsletterBriefingVersion.briefing_id == briefing.id).order_by(NewsletterBriefingVersion.version_number.desc())
    v_result = await db_session.execute(stmt)
    versions = v_result.scalars().all()
    
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[0].title == "Editor Edit"
    
    # Verify BriefingUpdated Event
    outbox_stmt = select(EventOutbox).where(EventOutbox.event_type == "BriefingUpdated")
    outbox_result = await db_session.execute(outbox_stmt)
    events = outbox_result.scalars().all()
    assert len(events) >= 1
    
@pytest.mark.asyncio
async def test_briefing_approval_emits_event(db_session):
    """Ensure BriefingApproved enters outbox."""
    service = NewsletterService(db_session)
    briefing = NewsletterBriefing(status="DRAFT")
    db_session.add(briefing)
    await db_session.flush()
    
    success = await service.approve_briefing(briefing.id)
    assert success is True
    
    assert briefing.status == "APPROVED"
    assert briefing.approved_at is not None
    
    outbox_stmt = select(EventOutbox).where(EventOutbox.event_type == "BriefingApproved")
    outbox_result = await db_session.execute(outbox_stmt)
    events = outbox_result.scalars().all()
    # Check the last emitted event
    assert events[-1].payload["briefing_id"] == briefing.id

@pytest.mark.asyncio
async def test_briefing_rejection_emits_event(db_session):
    """Ensure BriefingRejected enters outbox."""
    service = NewsletterService(db_session)
    briefing = NewsletterBriefing(status="DRAFT")
    db_session.add(briefing)
    await db_session.flush()
    
    success = await service.reject_briefing(briefing.id)
    assert success is True
    
    assert briefing.status == "REJECTED"
    
    outbox_stmt = select(EventOutbox).where(EventOutbox.event_type == "BriefingRejected")
    outbox_result = await db_session.execute(outbox_stmt)
    events = outbox_result.scalars().all()
    assert events[-1].payload["briefing_id"] == briefing.id

@pytest.mark.asyncio
async def test_dispatch_retry_safety(db_session):
    """Test atomic row lock (QUEUED to SENDING)."""
    from sqlalchemy import update
    
    # Create a queued delivery
    delivery = EmailDeliveryRecord(campaign_id=999, subscriber_id=888, status=EmailDeliveryStatus.QUEUED)
    db_session.add(delivery)
    await db_session.flush()
    
    # Simulate Worker 1 (Acquires lock)
    stmt1 = (
        update(EmailDeliveryRecord)
        .where(
            EmailDeliveryRecord.campaign_id == 999,
            EmailDeliveryRecord.subscriber_id == 888,
            EmailDeliveryRecord.status == "QUEUED"
        )
        .values(status="SENDING")
    )
    result1 = await db_session.execute(stmt1)
    assert result1.rowcount == 1 # Worker 1 successfully locked it
    
    # Simulate Worker 2 (Fails to acquire lock because it's no longer QUEUED)
    stmt2 = (
        update(EmailDeliveryRecord)
        .where(
            EmailDeliveryRecord.campaign_id == 999,
            EmailDeliveryRecord.subscriber_id == 888,
            EmailDeliveryRecord.status == "QUEUED"
        )
        .values(status="SENDING")
    )
    result2 = await db_session.execute(stmt2)
    assert result2.rowcount == 0 # Worker 2 aborted

@pytest.mark.asyncio
async def test_duplicate_briefing_approval(db_session):
    """Prove that calling Approve Briefing multiple times yields one event and no error."""
    service = NewsletterService(db_session)
    briefing = NewsletterBriefing(status="DRAFT")
    db_session.add(briefing)
    await db_session.flush()
    
    # First approval
    success1 = await service.approve_briefing(briefing.id)
    assert success1 is True
    
    # Second approval
    success2 = await service.approve_briefing(briefing.id)
    assert success2 is False # Safe rejection
    
    outbox_stmt = select(EventOutbox).where(EventOutbox.event_type == "BriefingApproved")
    outbox_result = await db_session.execute(outbox_stmt)
    events = outbox_result.scalars().all()
    # Check that only ONE event was emitted for this briefing
    events_for_this_briefing = [e for e in events if e.payload["briefing_id"] == briefing.id]
    assert len(events_for_this_briefing) == 1

@pytest.mark.asyncio
async def test_campaign_uniqueness_on_replay(db_session):
    """Prove that a briefing only ever creates one campaign, even on replay."""
    from app.newsletter.handlers import handle_briefing_approved
    from app.newsletter.models import NewsletterCampaign
    
    # Handle once
    await handle_briefing_approved(db_session, {"briefing_id": 8888})
    
    # Handle twice (simulate replay)
    await handle_briefing_approved(db_session, {"briefing_id": 8888}, is_replay=True)
    
    stmt = select(NewsletterCampaign).where(NewsletterCampaign.briefing_id == 8888)
    result = await db_session.execute(stmt)
    campaigns = result.scalars().all()
    
    # Only one campaign created
    assert len(campaigns) == 1

@pytest.mark.asyncio
async def test_bounce_suppression_prevents_dispatch(db_session):
    """Prove that emails in SuppressedEmail are excluded from the EmailDeliveryRecord generation loop."""
    from app.newsletter.handlers import handle_briefing_approved
    from app.newsletter.models import NewsletterSubscriber, SubscriptionStatus, SuppressedEmail, NewsletterCampaign
    
    # Add a clean subscriber
    sub1 = NewsletterSubscriber(email="clean@example.com", status=SubscriptionStatus.CONFIRMED, unsubscribe_token="tok1")
    db_session.add(sub1)
    
    # Add a bounced subscriber
    sub2 = NewsletterSubscriber(email="bounced@example.com", status=SubscriptionStatus.CONFIRMED, unsubscribe_token="tok2")
    db_session.add(sub2)
    
    # Add suppression
    suppression = SuppressedEmail(email="bounced@example.com", reason="HARD_BOUNCE")
    db_session.add(suppression)
    await db_session.flush()
    
    # Handle event
    await handle_briefing_approved(db_session, {"briefing_id": 9999})
    
    # Verify records
    stmt = select(EmailDeliveryRecord).join(NewsletterCampaign, NewsletterCampaign.id == EmailDeliveryRecord.campaign_id).where(NewsletterCampaign.briefing_id == 9999)
    result = await db_session.execute(stmt)
    deliveries = result.scalars().all()
    
    # Should only create delivery for clean@example.com
    assert len(deliveries) == 1
    assert deliveries[0].subscriber_id == sub1.id
