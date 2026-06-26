from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.events.models import EventOutbox
from app.models.distribution import DistributionJob, DistributionManifest
from app.models.editorial import EditorialDraft, EditorialDraftStatus, PublicationRecord
from app.tasks.editorial_tasks import _async_check_and_publish_scheduled_drafts_task

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_knowledge_workflow(monkeypatch):
    # Mock knowledge workflow to prevent actual LLM/embedding calls during distribution testing
    async def mock_execute(*args, **kwargs):
        return {
            "entities": [],
            "topics": [],
            "timeline": [],
            "relationships": []
        }
    monkeypatch.setattr("app.apps.tnt.knowledge_workflow.KnowledgeWorkflow.execute", mock_execute)
    return mock_execute

async def test_scheduled_draft_publishing_and_distribution(db_session, mock_knowledge_workflow):
    now = datetime.now(timezone.utc)
    from app.models.workspace import Workspace

    workspace = Workspace(name="Test Workspace", owner_type="user", owner_id="test_user")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # 1. Create a SCHEDULED draft ready to be published
    draft = EditorialDraft(
        workspace_id=workspace.id,
        title="Scheduled News",
        content="This will be published automatically.",
        author_id="test_user",
        status=EditorialDraftStatus.SCHEDULED.value,
        publish_at=now - timedelta(minutes=5)
    )
    db_session.add(draft)
    await db_session.commit()
    await db_session.refresh(draft)

    # 2. Run the celery beat task logic
    await _async_check_and_publish_scheduled_drafts_task()

    # Verify the ready draft is now PUBLISHED
    await db_session.refresh(draft)
    assert draft.status == EditorialDraftStatus.PUBLISHED.value

    # Verify PublicationRecord exists
    pub_stmt = select(PublicationRecord).where(PublicationRecord.published_by == "System")
    p_res = await db_session.execute(pub_stmt)
    pub_record = p_res.scalars().first()
    assert pub_record is not None

    # Verify DistributionManifest and Jobs
    manifest_stmt = select(DistributionManifest).where(DistributionManifest.publication_record_id == pub_record.id)
    m_res = await db_session.execute(manifest_stmt)
    manifest = m_res.scalars().first()
    assert manifest is not None

    job_stmt = select(DistributionJob).where(DistributionJob.manifest_id == manifest.id)
    j_res = await db_session.execute(job_stmt)
    jobs = j_res.scalars().all()
    assert len(jobs) >= 1  # Should at least have RSS job queued

    # Verify an EventOutbox was created
    stmt = select(EventOutbox).where(EventOutbox.event_type == "ArticlePublished")
    res = await db_session.execute(stmt)
    outbox_events = res.scalars().all()
    assert len(outbox_events) == 1

    event = outbox_events[0]
    assert event.payload["title"] == "Scheduled News"
