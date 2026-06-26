import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.analytics.projectors.cohort import CohortProjector
from app.core.projection.context import ProjectionContext
from app.core.projection.executor import ProjectionExecutor
from app.models.event import EventEnvelope
from app.models.growth import Cohort, CohortMembership, CohortRule


@pytest.mark.asyncio
async def test_dynamic_cohort_evaluation(db_session: AsyncSession):
    # Setup test dynamic cohort
    cohort_key = f"cohort_{uuid.uuid4().hex[:8]}"
    cohort = Cohort(
        key=cohort_key,
        name="Active Users Cohort",
        status="ACTIVE",
        subject_type="USER",
        refresh_mode="REAL_TIME"
    )
    db_session.add(cohort)
    await db_session.flush()

    # Rule: user must have viewed an article
    rule = CohortRule(
        cohort_id=cohort.id,
        rule_capability="EventRule",
        expression={
            "operator": "==",
            "field": "event_type",
            "value": "ARTICLE_VIEWED"
        }
    )
    db_session.add(rule)
    await db_session.commit()

    # Projector setup
    projector = CohortProjector()
    context = ProjectionContext(db_session)
    executor = ProjectionExecutor(db_session)

    user_id = "user100"

    # Event 1: Irrelevant event
    event1 = EventEnvelope(
        event_type="SIGNUP",
        subject_id=user_id,
        payload={}
    )
    batch1 = await projector.project(event1, context)
    await executor.execute_batch(batch1)
    await db_session.commit()

    # Verify no membership
    membership1 = (await db_session.execute(
        select(CohortMembership).where(CohortMembership.cohort_id == cohort.id)
    )).scalar_one_or_none()
    assert membership1 is None

    # Event 2: Triggering event
    event2 = EventEnvelope(
        event_type="ARTICLE_VIEWED",
        subject_id=user_id,
        payload={"article_id": 1}
    )
    batch2 = await projector.project(event2, context)
    await executor.execute_batch(batch2)
    await db_session.commit()

    # Verify entered cohort
    membership2 = (await db_session.execute(
        select(CohortMembership).where(CohortMembership.cohort_id == cohort.id)
    )).scalar_one_or_none()
    assert membership2 is not None
    assert membership2.status == "ENTERED"

@pytest.mark.asyncio
async def test_cohort_expression_evaluation():
    projector = CohortProjector()
    event = EventEnvelope(
        event_type="PURCHASED",
        subject_id="user1",
        payload={"plan": "Premium", "country": "US"}
    )

    expr1 = {
        "operator": "AND",
        "operands": [
            {"operator": "==", "field": "event_type", "value": "PURCHASED"},
            {"operator": "==", "field": "payload.country", "value": "US"}
        ]
    }
    assert projector._evaluate_expression(expr1, event) is True

    expr2 = {
        "operator": "AND",
        "operands": [
            {"operator": "==", "field": "event_type", "value": "PURCHASED"},
            {"operator": "==", "field": "payload.country", "value": "CA"}
        ]
    }
    assert projector._evaluate_expression(expr2, event) is False
