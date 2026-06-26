import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.analytics.projectors.funnel import FunnelProjector
from app.core.projection.context import ProjectionContext
from app.core.projection.executor import ProjectionExecutor
from app.models.event import EventEnvelope
from app.models.growth import Funnel, FunnelMetrics, FunnelState, FunnelStep
from app.models.user import utc_now


@pytest.mark.asyncio
async def test_funnel_progression_and_metrics(db_session: AsyncSession):
    # Setup test funnel
    funnel_key = f"funnel_{uuid.uuid4().hex[:8]}"
    funnel = Funnel(
        key=funnel_key,
        name="Test Funnel",
        status="ACTIVE",
        subject_type="USER",
        time_window_seconds=3600
    )
    db_session.add(funnel)
    await db_session.flush()

    step1 = FunnelStep(
        funnel_id=funnel.id,
        step_order=1,
        name="View",
        event_matcher={"type": "VIEW", "conditions": {"page": "home"}}
    )
    step2 = FunnelStep(
        funnel_id=funnel.id,
        step_order=2,
        name="Signup",
        event_matcher={"type": "SIGNUP", "conditions": {}}
    )
    db_session.add_all([step1, step2])
    await db_session.commit()

    # Projector setup
    projector = FunnelProjector()
    context = ProjectionContext(db_session)
    executor = ProjectionExecutor(db_session)

    user_id = "user123"

    # Event 1: Trigger step 1
    event1 = EventEnvelope(
        event_type="VIEW",
        subject_id=user_id,
        payload={"page": "home"}
    )
    batch1 = await projector.project(event1, context)
    await executor.execute_batch(batch1)
    await db_session.commit()

    # Verify state and metrics
    state = (await db_session.execute(select(FunnelState).where(FunnelState.funnel_id == funnel.id))).scalar_one()
    assert state.current_step_order == 1
    assert not state.is_completed

    metrics = (await db_session.execute(select(FunnelMetrics).where(FunnelMetrics.funnel_id == funnel.id))).scalar_one()
    assert metrics.total_started == 1
    assert metrics.total_completed == 0
    assert metrics.step_counts == {"1": 1}
    assert metrics.conversion_rate == 0.0

    # Event 2: Trigger step 2 (complete)
    event2 = EventEnvelope(
        event_type="SIGNUP",
        subject_id=user_id,
        payload={}
    )
    batch2 = await projector.project(event2, context)
    await executor.execute_batch(batch2)
    await db_session.commit()

    # Verify completion
    await db_session.refresh(state)
    assert state.current_step_order == 2
    assert state.is_completed
    assert state.completed_at is not None

    await db_session.refresh(metrics)
    assert metrics.total_completed == 1
    assert metrics.step_counts == {"1": 1, "2": 1}
    assert metrics.conversion_rate == 1.0
    assert metrics.dropoff_rate == 0.0

@pytest.mark.asyncio
async def test_funnel_expiration(db_session: AsyncSession):
    funnel_key = f"funnel_{uuid.uuid4().hex[:8]}"
    funnel = Funnel(
        key=funnel_key,
        name="Expiration Funnel",
        status="ACTIVE",
        subject_type="USER",
        time_window_seconds=1 # 1 second window
    )
    db_session.add(funnel)
    await db_session.flush()

    step1 = FunnelStep(
        funnel_id=funnel.id,
        step_order=1,
        name="S1",
        event_matcher={"type": "E1"}
    )
    step2 = FunnelStep(
        funnel_id=funnel.id,
        step_order=2,
        name="S2",
        event_matcher={"type": "E2"}
    )
    db_session.add_all([step1, step2])
    await db_session.commit()

    projector = FunnelProjector()
    context = ProjectionContext(db_session)
    executor = ProjectionExecutor(db_session)

    user_id = "user_exp"

    # Step 1
    event1 = EventEnvelope(event_type="E1", subject_id=user_id)
    batch1 = await projector.project(event1, context)
    await executor.execute_batch(batch1)
    await db_session.commit()

    # Modify state to simulate expiration
    state = (await db_session.execute(select(FunnelState).where(FunnelState.funnel_id == funnel.id))).scalar_one()
    state.expires_at = utc_now() - timedelta(seconds=10)
    await db_session.commit()

    # Step 2
    event2 = EventEnvelope(event_type="E2", subject_id=user_id)
    batch2 = await projector.project(event2, context)
    await executor.execute_batch(batch2)
    await db_session.commit()

    # State should not progress
    await db_session.refresh(state)
    assert state.current_step_order == 1
    assert not state.is_completed
