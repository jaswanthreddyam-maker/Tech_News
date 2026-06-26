import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.generation.capabilities.base import CapabilityRegistry
from app.intelligence.generation.capabilities.implementations import RAGCapability, SummaryCapability
from app.intelligence.generation.context import CapabilityContext
from app.models.intelligence import GenerationTelemetry


@pytest.mark.asyncio
async def test_capability_registry(db_session: AsyncSession):
    registry = CapabilityRegistry()
    registry.register(SummaryCapability())
    registry.register(RAGCapability())

    # Execute SummaryCapability
    context = CapabilityContext(
        capability_name="SummaryCapability",
        query="Summarize AI advancements"
    )
    cap = registry.get("SummaryCapability")
    result = await cap.execute(db_session, context)

    assert "mock generation" in result["answer"]
    assert result["telemetry"]["total_latency_ms"] >= 0

    # Verify telemetry
    telemetry = (await db_session.execute(
        select(GenerationTelemetry).where(GenerationTelemetry.query_text == "Summarize AI advancements")
    )).scalars().first()

    assert telemetry is not None
    assert telemetry.capability_name == "SummaryCapability"
    assert telemetry.tool_count == 0

    # Ensure profile loaded correctly (fallback will use Fast profile values)
    assert telemetry.provider_name == "mock" # since we mocked the chat provider
