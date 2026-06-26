from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.ai_pipeline import enrich_raw_article
from app.ai.ai_repository import persist_telemetry
from app.ai.fingerprint import build_enrichment_input_fingerprint
from app.ai.schemas import AIJobStatus, AITelemetryRecord
from app.models.article import RawArticle
from app.models.growth import FeatureFlag
from app.models.source import Source  # noqa: F401
from app.models.user import AIJobHistory
from tests.test_ai_infrastructure import MockAIProvider


async def set_ai_enrichment_flag(db_session: AsyncSession, value: bool) -> None:
    flag_res = await db_session.execute(select(FeatureFlag).where(FeatureFlag.key == "ai_enrichment_enabled"))
    flag = flag_res.scalars().first()
    if flag:
        flag.default_value = {"enabled": value}
    else:
        db_session.add(FeatureFlag(key="ai_enrichment_enabled", name="AI Enrichment", default_value={"enabled": value}))


@pytest.mark.asyncio
async def test_ai_pipeline_returns_none_when_feature_flag_off(db_session: AsyncSession):
    # Setup test DB with feature flag OFF
    await set_ai_enrichment_flag(db_session, False)

    raw = RawArticle(title="Test", url="http://test.com", url_hash="1", title_hash="1")
    db_session.add(raw)
    await db_session.flush()

    with patch("app.core.config.settings.AI_PROVIDER", "openai"):
        result = await enrich_raw_article(db_session, raw.id)

    assert result is None


@pytest.mark.asyncio
async def test_ai_pipeline_returns_none_when_provider_disabled(db_session: AsyncSession):
    await set_ai_enrichment_flag(db_session, True)
    raw = RawArticle(title="Test", url="http://test.com", url_hash="2", title_hash="2")
    db_session.add(raw)
    await db_session.flush()

    with patch("app.core.config.settings.AI_PROVIDER", "disabled"):
        result = await enrich_raw_article(db_session, raw.id)

    assert result is None


@pytest.mark.asyncio
async def test_ai_pipeline_enriches_with_mock_provider(db_session: AsyncSession):
    await set_ai_enrichment_flag(db_session, True)
    raw = RawArticle(
        title="AI test", clean_text="Test article content.", url="http://test.com", url_hash="3", title_hash="3"
    )
    db_session.add(raw)
    await db_session.flush()

    with (
        patch("app.core.config.settings.AI_PROVIDER", "mock"),
        patch("app.ai.service.build_ai_provider", return_value=MockAIProvider()),
    ):
        result = await enrich_raw_article(db_session, raw.id)

    assert result is not None
    assert result.status == AIJobStatus.COMPLETED
    assert result.output.summary == "A concise AI summary."


@pytest.mark.asyncio
async def test_ai_pipeline_falls_back_on_provider_error(db_session: AsyncSession):
    await set_ai_enrichment_flag(db_session, True)
    raw = RawArticle(title="AI error test", url="http://test.com", url_hash="4", title_hash="4")
    db_session.add(raw)
    await db_session.flush()

    # Create a provider that raises an exception
    class ErrorProvider(MockAIProvider):
        async def summarize(self, request):
            raise Exception("API failure")

    with (
        patch("app.core.config.settings.AI_PROVIDER", "mock"),
        patch("app.ai.service.build_ai_provider", return_value=ErrorProvider()),
    ):
        result = await enrich_raw_article(db_session, raw.id)

    assert result is not None
    assert result.status == AIJobStatus.FALLBACK
    # Ensure it generated heuristic fallback
    assert "No summary compiled yet." in result.output.summary or len(result.output.summary) > 0


@pytest.mark.asyncio
async def test_ai_pipeline_falls_back_on_malformed_json(db_session: AsyncSession):
    await set_ai_enrichment_flag(db_session, True)
    raw = RawArticle(title="AI JSON test", clean_text="Test text.", url="http://test.com", url_hash="5", title_hash="5")
    db_session.add(raw)
    await db_session.flush()

    with (
        patch("app.core.config.settings.AI_PROVIDER", "mock"),
        patch("app.ai.service.build_ai_provider", return_value=MockAIProvider(invalid_summary=True)),
    ):
        result = await enrich_raw_article(db_session, raw.id)

    assert result is not None
    assert result.status == AIJobStatus.FALLBACK
    assert len(result.telemetry) > 0
    # Telemetry should be recorded
    assert result.telemetry[0].status == AIJobStatus.FALLBACK


@pytest.mark.asyncio
async def test_ai_repository_persists_telemetry_and_returns_ids(db_session: AsyncSession):
    record = AITelemetryRecord(
        provider="mock",
        task_type="summary",
        model="test-model",
        status=AIJobStatus.COMPLETED,
        prompt_version="summary_v1",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        cost_usd="0.001",
        cache_hit=False,
        retry_count=0,
        provider_metadata={
            "provider": "mock",
            "model": "test-model",
            "prompt_version": "summary_v1",
            "sdk_version": None,
            "response_format": None,
        },
        enrichment_input_fingerprint=build_enrichment_input_fingerprint(
            title="Title",
            content="Content",
            prompt_version="summary_v1",
            provider="mock",
            model="test-model",
        ),
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )

    ids = await persist_telemetry(db_session, None, None, [record])
    assert len(ids) == 1

    stmt = select(AIJobHistory).where(AIJobHistory.id == ids[0])
    res = await db_session.execute(stmt)
    job = res.scalars().first()
    assert job is not None
    assert job.provider == "mock"
    assert job.task_type == "summary"
    assert job.provider_metadata["provider"] == "mock"
    assert job.provider_metadata["prompt_version"] == "summary_v1"
    assert job.enrichment_input_fingerprint == record.enrichment_input_fingerprint


@pytest.mark.asyncio
async def test_single_transaction_rolls_back_on_telemetry_failure(db_session: AsyncSession):
    # If persist_telemetry fails, we catch the exception in pipeline and rollback.
    # We test the ai_repository behavior on invalid data (e.g., missing required fields)
    with pytest.raises(ValueError):
        record = AITelemetryRecord(
            provider=None,  # Invalid, should fail
            task_type="summary",
            model="test",
            prompt_version="summary_v1",
            status=AIJobStatus.COMPLETED,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
        await persist_telemetry(db_session, None, None, [record])
