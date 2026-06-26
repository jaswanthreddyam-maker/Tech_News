import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.events.models import EventOutbox
from app.models.growth import FeatureFlag
from main import app


@pytest.mark.asyncio
async def test_evaluate_flags_default_value(db_session: AsyncSession, auth_headers: dict):
    unique_key = f"test_flag_{uuid.uuid4().hex[:8]}"
    # Create a feature flag
    flag = FeatureFlag(
        key=unique_key,
        name="Test Flag",
        default_value="default",
        environment_states={"test": True},
        rules=[]
    )
    db_session.add(flag)
    await db_session.commit()

    context = {
        "environment": "test",
        "user_id": "user123"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/growth/flags/evaluate", json=context, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert unique_key in data
    assert data[unique_key]["value"] == "default"
    assert data[unique_key]["reason"] == "Default value fallback"
    assert isinstance(data[unique_key]["trace"], list)

    # Verify telemetry
    result = await db_session.execute(select(EventOutbox).where(EventOutbox.event_type == "GROWTH_EVALUATED"))
    outbox_events = result.scalars().all()
    assert len(outbox_events) >= 1
    assert any(e.payload["flag_key"] == unique_key for e in outbox_events)


@pytest.mark.asyncio
async def test_evaluate_flags_percentage_rule(db_session: AsyncSession, auth_headers: dict):
    unique_key = f"test_percent_{uuid.uuid4().hex[:8]}"
    # Create a feature flag with percentage rule
    flag = FeatureFlag(
        key=unique_key,
        name="Test Percent",
        default_value=False,
        environment_states={"test": True},
        rules=[
            {
                "rule_type": "PercentageRule",
                "priority": 300,
                "config": {"percentage": 100, "value": True}
            }
        ]
    )
    db_session.add(flag)
    await db_session.commit()

    context = {
        "environment": "test",
        "user_id": "user_always_100"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/growth/flags/evaluate", json=context, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data[unique_key]["value"] == True
    assert data[unique_key]["reason"] == "Rule match"
    assert len(data[unique_key]["trace"]) > 0
    assert data[unique_key]["trace"][0]["matched"] is True

@pytest.mark.asyncio
async def test_evaluate_flags_disabled_env(db_session: AsyncSession, auth_headers: dict):
    unique_key = f"test_env_{uuid.uuid4().hex[:8]}"
    # Environment disabled
    flag = FeatureFlag(
        key=unique_key,
        name="Test Env",
        default_value=False,
        environment_states={"test": False},
        rules=[
            {
                "rule_type": "PercentageRule",
                "priority": 300,
                "config": {"percentage": 100, "value": True}
            }
        ]
    )
    db_session.add(flag)
    await db_session.commit()

    context = {
        "environment": "test",
        "user_id": "user123"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/growth/flags/evaluate", json=context, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data[unique_key]["value"] == False
    assert "disabled" in data[unique_key]["reason"]
    assert len(data[unique_key]["trace"]) == 0

@pytest.mark.asyncio
async def test_rule_priority_sorting(db_session: AsyncSession, auth_headers: dict):
    unique_key = f"test_priority_{uuid.uuid4().hex[:8]}"
    # Provide two rules, CountryRule (Priority 600) and UserRule (Priority 900)
    # The array has CountryRule first, but engine should evaluate UserRule first.
    flag = FeatureFlag(
        key=unique_key,
        name="Test Priority",
        default_value="default",
        environment_states={"test": True},
        rules=[
            {
                "rule_type": "CountryRule",
                "priority": 600,
                "config": {"countries": ["US"], "value": "country_val"}
            },
            {
                "rule_type": "UserRule",
                "priority": 900,
                "config": {"user_ids": ["user123"], "value": "user_val"}
            }
        ]
    )
    db_session.add(flag)
    await db_session.commit()

    context = {
        "environment": "test",
        "user_id": "user123",
        "country": "US"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/growth/flags/evaluate", json=context, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # Should match UserRule first because of priority
    assert data[unique_key]["value"] == "user_val"
    assert data[unique_key]["reason"] == "Rule match"

    # The trace should only have 1 entry (UserRule matched, engine exits early)
    trace = data[unique_key]["trace"]
    assert len(trace) == 1
    assert trace[0]["rule_name"] == "UserRule"
    assert trace[0]["matched"] is True
