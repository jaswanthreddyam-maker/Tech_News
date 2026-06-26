import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.events.models import EventOutbox
from app.models.growth import Experiment, ExperimentAssignment, ExperimentVariant
from main import app


@pytest.mark.asyncio
async def test_experiment_evaluation_allocation(db_session: AsyncSession, auth_headers: dict):
    experiment_key = f"exp_{uuid.uuid4().hex[:8]}"

    experiment = Experiment(
        key=experiment_key,
        name="Test Experiment Allocation",
        status="RUNNING",
        subject_type="USER",
        assignment_strategy="HASH",
        allocation_percentage=100,
        environment_states={"test": True},
        rules=[]
    )
    db_session.add(experiment)
    await db_session.flush()

    variant_a = ExperimentVariant(
        experiment_id=experiment.id,
        key="treatment_a",
        name="Treatment A",
        weight=50,
        config={"color": "red"}
    )
    variant_b = ExperimentVariant(
        experiment_id=experiment.id,
        key="treatment_b",
        name="Treatment B",
        weight=50,
        config={"color": "blue"}
    )
    db_session.add_all([variant_a, variant_b])
    await db_session.commit()

    context = {
        "environment": "test",
        "user_id": "user123"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/experiments/evaluate", json=context, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert experiment_key in data
    assigned_variant = data[experiment_key]
    assert assigned_variant is not None
    assert assigned_variant["key"] in ["treatment_a", "treatment_b"]

    # Verify assignment is persisted
    assignment_result = await db_session.execute(select(ExperimentAssignment).where(ExperimentAssignment.experiment_id == experiment.id))
    assignments = assignment_result.scalars().all()
    assert len(assignments) == 1
    assert assignments[0].exposure_count == 1
    assert assignments[0].subject_id == "user123"

    # Verify events
    event_result = await db_session.execute(
        select(EventOutbox)
        .where(EventOutbox.event_type.in_(["EXPERIMENT_ASSIGNED", "EXPERIMENT_EXPOSED"]))
        .order_by(EventOutbox.id)
    )
    events = event_result.scalars().all()
    # Should have both ASSIGNED and EXPOSED for new assignment
    experiment_events = [e for e in events if e.payload.get("experiment_key") == experiment_key]
    assert len(experiment_events) >= 2
    types = [e.event_type for e in experiment_events]
    assert "EXPERIMENT_ASSIGNED" in types
    assert "EXPERIMENT_EXPOSED" in types

@pytest.mark.asyncio
async def test_experiment_evaluation_mutual_exclusion(db_session: AsyncSession, auth_headers: dict):
    # Subject already in experiment 1 (Group A) -> Should not get assigned to experiment 2 (Group A)
    mutex_group = f"mutex_{uuid.uuid4().hex[:8]}"

    exp1 = Experiment(
        key=f"exp1_{uuid.uuid4().hex[:8]}",
        name="Exp 1",
        status="RUNNING",
        mutual_exclusion_group_id=mutex_group,
        environment_states={"test": True}
    )
    exp2 = Experiment(
        key=f"exp2_{uuid.uuid4().hex[:8]}",
        name="Exp 2",
        status="RUNNING",
        mutual_exclusion_group_id=mutex_group,
        environment_states={"test": True}
    )
    db_session.add_all([exp1, exp2])
    await db_session.flush()

    var1 = ExperimentVariant(experiment_id=exp1.id, key="v1", name="V1", weight=100)
    var2 = ExperimentVariant(experiment_id=exp2.id, key="v2", name="V2", weight=100)
    db_session.add_all([var1, var2])
    await db_session.flush()

    # Create assignment for Exp1
    assignment = ExperimentAssignment(
        experiment_id=exp1.id,
        variant_id=var1.id,
        subject_id="user_mutex",
        subject_type="USER",
        assignment_hash="hash123",
        assignment_version="v1"
    )
    db_session.add(assignment)
    await db_session.commit()

    context = {
        "environment": "test",
        "user_id": "user_mutex"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/experiments/evaluate", json=context, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # exp1 should be evaluated and return V1
    assert data[exp1.key]["key"] == "v1"
    # exp2 should return null/None due to mutex group conflict
    assert data[exp2.key] is None
