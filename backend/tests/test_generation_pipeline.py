import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.generation.capabilities.base import MockChatProvider
from app.intelligence.generation.context import AIContext
from app.intelligence.generation.context_stages import (
    ContextCollector,
    ContextCompressor,
    ContextDeduplicator,
    TokenBudgetAllocator,
)
from app.intelligence.generation.pipeline import GenerationPipeline
from app.intelligence.generation.prompt import PromptTemplate
from app.models.intelligence import GenerationTelemetry


@pytest.mark.asyncio
async def test_generation_pipeline_no_retrieval(db_session: AsyncSession):
    context = AIContext(
        query="Explain RAG",
    )

    template = PromptTemplate(system_prompt="Test")

    pipeline = GenerationPipeline(
        chat_provider=MockChatProvider(),
        prompt_template=template,
        retrievers=[],
        context_stages=[
            ContextCollector(),
            ContextDeduplicator(),
            ContextCompressor(),
            TokenBudgetAllocator()
        ]
    )

    result = await pipeline.execute(db_session, context, stream=False)

    assert "mock generation" in result["answer"]
    assert result["provider"] == "mock"
    assert result["model"] == "mock-model"

    # Verify telemetry was inserted
    telemetry = (await db_session.execute(
        select(GenerationTelemetry).where(GenerationTelemetry.query_text == "Explain RAG")
    )).scalars().first()

    assert telemetry is not None
    assert telemetry.total_latency_ms > 0
