from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

# Ensure the projector is registered
import app.analytics.projectors.article  # noqa: F401

# Ensure the projector is registered
from app.core.projection.engine import ProjectionEngine, ReplayEngine
from app.core.projection.models import ProjectionCheckpoint, ProjectionFailure
from app.core.projection.registry import projector_registry
from app.core.projection.source import EventEnvelopeSource
from app.models.analytics import ArticleMetrics
from app.models.event import EventCategory, EventEnvelope, EventSubjectType


@pytest_asyncio.fixture
async def clear_analytics(db_session):
    await db_session.execute(delete(ProjectionCheckpoint))
    await db_session.execute(delete(ProjectionFailure))
    await db_session.execute(delete(ArticleMetrics))
    await db_session.execute(delete(EventEnvelope))
    await db_session.commit()
    yield

@pytest.mark.asyncio
async def test_idempotency_duplicate_detection(db_session, clear_analytics):
    # 1. Create a single event
    event = EventEnvelope(
        category=EventCategory.ANALYTICS,
        event_type="ARTICLE_VIEWED",
        subject_type=EventSubjectType.ARTICLE,
        subject_id="art-123",
        provider="TEST",
        occurred_at=datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    engine = ProjectionEngine(db_session)

    # 2. Ingest the event TWICE
    await engine.process_event(event)
    await engine.process_event(event)
    await db_session.commit()

    # 3. Verify ArticleMetrics has exactly 1 view (idempotent)
    stmt = select(ArticleMetrics).where(ArticleMetrics.article_id == "art-123")
    metrics = (await db_session.execute(stmt)).scalar_one()
    assert metrics.views == 1

    # 4. Verify exactly 1 checkpoint exists
    chkpt_stmt = select(ProjectionCheckpoint).where(
        ProjectionCheckpoint.event_id == event.id,
        ProjectionCheckpoint.projector_name == "ArticleMetricsProjector"
    )
    checkpoints = (await db_session.execute(chkpt_stmt)).scalars().all()
    assert len(checkpoints) == 1

@pytest.mark.asyncio
async def test_full_replay(db_session, clear_analytics):
    # 1. Create a few events
    event1 = EventEnvelope(
        category=EventCategory.ANALYTICS,
        event_type="ARTICLE_VIEWED",
        subject_type=EventSubjectType.ARTICLE,
        subject_id="art-123",
        provider="TEST",
        occurred_at=datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)
    )
    event2 = EventEnvelope(
        category=EventCategory.ANALYTICS,
        event_type="ARTICLE_COMPLETED",
        subject_type=EventSubjectType.ARTICLE,
        subject_id="art-123",
        provider="TEST",
        occurred_at=datetime(2026, 6, 14, 12, 5, tzinfo=timezone.utc),
        payload={"read_time_seconds": 120}
    )
    db_session.add_all([event1, event2])
    await db_session.commit()

    engine = ProjectionEngine(db_session)
    source = EventEnvelopeSource(db_session)

    # 2. Ingest events initially
    await engine.process_stream(source)
    await db_session.commit()

    # 3. Delete projections directly (simulate disaster/migration)
    await db_session.execute(delete(ArticleMetrics))
    await db_session.commit()

    # 4. Execute Replay Service
    replay_svc = ReplayEngine(db_session, engine)

    # Needs to clear checkpoints explicitly if we rebuild specific projectors
    projectors = projector_registry.get_projectors_for_event("ARTICLE_VIEWED")
    await replay_svc.replay(source, projectors=projectors)
    await db_session.commit()

    # 5. Verify read models are rebuilt exactly the same
    stmt = select(ArticleMetrics).where(ArticleMetrics.article_id == "art-123")
    metrics = (await db_session.execute(stmt)).scalar_one()
    assert metrics.views == 1
    assert metrics.completed_reads == 1
    assert metrics.completion_rate == 1.0
    assert metrics.total_read_time_seconds == 120

@pytest.mark.asyncio
async def test_version_updatability(db_session, clear_analytics):
    # Create event
    event = EventEnvelope(
        category=EventCategory.ANALYTICS,
        event_type="ARTICLE_VIEWED",
        subject_type=EventSubjectType.ARTICLE,
        subject_id="art-123",
        provider="TEST",
        occurred_at=datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)
    )
    db_session.add(event)
    await db_session.commit()

    # Ingest event initially
    engine = ProjectionEngine(db_session)
    await engine.process_event(event)
    await db_session.commit()

    chkpt_stmt = select(ProjectionCheckpoint).where(
        ProjectionCheckpoint.event_id == event.id,
        ProjectionCheckpoint.projector_name == "ArticleMetricsProjector"
    )
    checkpoint = (await db_session.execute(chkpt_stmt)).scalar_one()

    # Store old version
    old_version = checkpoint.projector_version

    # Simulate a version upgrade dynamically
    projectors = projector_registry.get_projectors_for_event("ARTICLE_VIEWED")
    projector = next(p for p in projectors if p.name == "ArticleMetricsProjector")
    original_version = projector.__class__.version
    projector.__class__.version = property(lambda self: 99) # Mock version update

    try:
        # Replay
        replay_svc = ReplayEngine(db_session, engine)
        source = EventEnvelopeSource(db_session)
        await replay_svc.replay(source, projectors=[projector])
        await db_session.commit()

        # Verify checkpoint has new version
        chkpt_stmt = select(ProjectionCheckpoint).where(
            ProjectionCheckpoint.event_id == event.id,
            ProjectionCheckpoint.projector_name == "ArticleMetricsProjector"
        )
        checkpoint = (await db_session.execute(chkpt_stmt)).scalar_one()
        assert checkpoint.projector_version == 99
        assert old_version != 99
    finally:
        # Restore version
        projector.__class__.version = original_version

@pytest.mark.asyncio
async def test_failure_capturing(db_session, clear_analytics):
    # Create event
    event = EventEnvelope(
        category=EventCategory.ANALYTICS,
        event_type="ARTICLE_VIEWED",
        subject_type=EventSubjectType.ARTICLE,
        subject_id="art-123",
        provider="TEST",
        occurred_at=datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)
    )
    db_session.add(event)
    await db_session.commit()

    # Inject failure dynamically
    projectors = projector_registry.get_projectors_for_event("ARTICLE_VIEWED")
    projector = next(p for p in projectors if p.name == "ArticleMetricsProjector")

    original_project = projector.project

    async def mock_project(*args, **kwargs):
        raise ValueError("Simulated projection error")

    projector.project = mock_project

    try:
        engine = ProjectionEngine(db_session)
        # Should not raise exception out to caller, should capture in ProjectionFailure
        await engine.process_event(event)
        await db_session.commit()

        fail_stmt = select(ProjectionFailure).where(
            ProjectionFailure.event_id == event.id,
            ProjectionFailure.projector_name == "ArticleMetricsProjector"
        )
        failure = (await db_session.execute(fail_stmt)).scalar_one()
        assert failure.error == "Simulated projection error"
        assert failure.attempt_count == 1
    finally:
        # Restore
        projector.project = original_project

@pytest.mark.asyncio
async def test_dry_run(db_session, clear_analytics):
    # Create event
    event = EventEnvelope(
        category=EventCategory.ANALYTICS,
        event_type="ARTICLE_VIEWED",
        subject_type=EventSubjectType.ARTICLE,
        subject_id="art-123",
        provider="TEST",
        occurred_at=datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)
    )
    db_session.add(event)
    await db_session.commit()

    engine = ProjectionEngine(db_session)
    source = EventEnvelopeSource(db_session)

    # Replay with dry run
    replay_svc = ReplayEngine(db_session, engine)
    await replay_svc.replay(source, dry_run=True)
    await db_session.commit()

    # Verify no checkpoints created
    chkpt_stmt = select(ProjectionCheckpoint).where(
        ProjectionCheckpoint.event_id == event.id,
        ProjectionCheckpoint.projector_name == "ArticleMetricsProjector"
    )
    checkpoints = (await db_session.execute(chkpt_stmt)).scalars().all()
    assert len(checkpoints) == 0

    # Verify no read models populated
    stmt = select(ArticleMetrics).where(ArticleMetrics.article_id == "art-123")
    metrics = (await db_session.execute(stmt)).scalars().all()
    assert len(metrics) == 0
