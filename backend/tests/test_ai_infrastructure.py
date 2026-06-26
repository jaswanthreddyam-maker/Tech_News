import asyncio
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.ai.cache import MemoryAICache
from app.ai.config import AIConfig
from app.ai.cost import calculate_cost_usd
from app.ai.exceptions import AIConfigurationError, AIProviderError, AIProviderTimeout, AIResponseValidationError
from app.ai.fingerprint import build_enrichment_input_fingerprint
from app.ai.providers.base import BaseAIProvider
from app.ai.providers.factory import build_ai_provider
from app.ai.retry import RetryPolicy, retry_async
from app.ai.schemas import (
    AIEnrichmentOutput,
    AIJobStatus,
    AIProviderResponse,
    AITaskRequest,
    AITaskType,
    ArticleAIInput,
    SentimentLabel,
    TokenUsage,
)
from app.ai.service import AIService, PromptRegistry
from app.core.config import Settings


class MockAIProvider(BaseAIProvider):
    provider_name = "mock"
    default_model = "phase4-foundation"

    def __init__(self, *, invalid_summary: bool = False) -> None:
        self.invalid_summary = invalid_summary
        self.calls: dict[AITaskType, int] = {
            AITaskType.SUMMARY: 0,
            AITaskType.KEYWORDS: 0,
            AITaskType.TAGS: 0,
            AITaskType.SENTIMENT: 0,
        }

    async def summarize(self, request: AITaskRequest) -> AIProviderResponse:
        self.calls[AITaskType.SUMMARY] += 1
        payload = {"not_summary": "bad"} if self.invalid_summary else {"summary": "A concise AI summary."}
        return self._response(request, payload)

    async def generate_keywords(self, request: AITaskRequest) -> AIProviderResponse:
        self.calls[AITaskType.KEYWORDS] += 1
        return self._response(request, {"keywords": ["AI", "chips", "AI"]})

    async def generate_tags(self, request: AITaskRequest) -> AIProviderResponse:
        self.calls[AITaskType.TAGS] += 1
        return self._response(request, {"tags": ["artificial-intelligence", "semiconductors"]})

    async def analyze_sentiment(self, request: AITaskRequest) -> AIProviderResponse:
        self.calls[AITaskType.SENTIMENT] += 1
        return self._response(request, {"sentiment": "positive"})

    def _response(self, request: AITaskRequest, payload: dict) -> AIProviderResponse:
        return AIProviderResponse(
            provider=self.provider_name,
            model=request.model,
            task_type=request.task_type,
            payload=payload,
            usage=TokenUsage(prompt_tokens=100, completion_tokens=25),
            latency_ms=12,
        )


class SlowAIProvider(MockAIProvider):
    async def summarize(self, request: AITaskRequest) -> AIProviderResponse:
        await asyncio.sleep(0.05)
        return await super().summarize(request)


def test_prompt_loader_reads_versioned_prompt() -> None:
    prompt, _ = PromptRegistry().get_prompt("summary_v1")

    assert "Prompt Version: 1" in prompt
    assert "single valid JSON object" in prompt
    assert '{"summary"' in prompt


def test_settings_separates_app_env_from_debug() -> None:
    loaded = Settings(_env_file=None, APP_ENV="staging", ENV="development", DEBUG=False)

    assert loaded.effective_environment == "staging"
    assert loaded.DEBUG is False


def test_settings_rejects_non_boolean_debug_values() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV="development", DEBUG="release")


def test_settings_rejects_unknown_app_env_values() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV="release", DEBUG=False)


def test_provider_factory_rejects_unknown_provider() -> None:
    with pytest.raises(AIConfigurationError):
        build_ai_provider("not-a-provider")


def test_disabled_provider_is_default_factory_option() -> None:
    provider = build_ai_provider("disabled")

    assert provider.provider_name == "disabled"


@pytest.mark.asyncio
async def test_ai_service_enriches_article_with_structured_mock_provider() -> None:
    provider = MockAIProvider()
    service = AIService(providers=[provider], config=AIConfig(provider="mock"))
    article = ArticleAIInput(title="AI chip launch", content="A company launched a new AI accelerator.")

    result = await service.enrich_article(article)

    assert result.status == AIJobStatus.COMPLETED
    assert result.output.summary == "A concise AI summary."
    assert result.output.keywords == ["AI", "chips"]
    assert result.output.tags == ["artificial-intelligence", "semiconductors"]
    assert result.output.sentiment == SentimentLabel.POSITIVE
    assert len(result.telemetry) == 4
    assert all(record.provider == "mock" for record in result.telemetry)
    assert all(record.provider_metadata["provider"] == "mock" for record in result.telemetry)
    assert all(record.provider_metadata["model"] == service.config.summary_model for record in result.telemetry)
    assert all(record.enrichment_input_fingerprint for record in result.telemetry)

    summary_fingerprint = build_enrichment_input_fingerprint(
        title=article.title,
        content=article.content,
        prompt_version="summary_v1",
        provider="mock",
        model=service.config.summary_model,
    )
    assert result.telemetry[0].enrichment_input_fingerprint == summary_fingerprint


@pytest.mark.asyncio
async def test_ai_service_raises_on_invalid_structured_output_without_fallback() -> None:
    service = AIService(providers=[MockAIProvider(invalid_summary=True)], config=AIConfig(provider="mock"))
    article = ArticleAIInput(title="AI chip launch", content="A company launched a new AI accelerator.")

    with pytest.raises(AIResponseValidationError):
        await service.enrich_article(article)


@pytest.mark.asyncio
async def test_ai_service_returns_fallback_when_provider_output_is_invalid() -> None:
    service = AIService(providers=[MockAIProvider(invalid_summary=True)], config=AIConfig(provider="mock"))
    article = ArticleAIInput(title="AI chip launch", content="A company launched a new AI accelerator.")
    fallback = AIEnrichmentOutput(
        summary="Heuristic summary.",
        keywords=["ai"],
        tags=["artificial-intelligence"],
        sentiment=SentimentLabel.NEUTRAL,
    )

    result = await service.enrich_article(article, fallback=fallback)

    assert result.status == AIJobStatus.FALLBACK
    assert result.output.summary == "Heuristic summary."
    assert result.error


@pytest.mark.asyncio
async def test_ai_service_uses_cache_for_repeated_task_payloads() -> None:
    provider = MockAIProvider()
    service = AIService(providers=[provider], config=AIConfig(provider="mock"), cache=MemoryAICache())
    article = ArticleAIInput(title="AI chip launch", content="A company launched a new AI accelerator.")

    first = await service.enrich_article(article)
    second = await service.enrich_article(article)

    assert first.status == AIJobStatus.COMPLETED
    assert second.status == AIJobStatus.COMPLETED
    assert provider.calls[AITaskType.SUMMARY] == 1
    assert all(record.cache_hit for record in second.telemetry)


@pytest.mark.asyncio
async def test_retry_async_retries_retryable_provider_errors() -> None:
    attempts = 0

    async def flaky_operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise AIProviderError("temporary failure")
        return "ok"

    result, retry_count = await retry_async(
        flaky_operation,
        policy=RetryPolicy(max_attempts=3, base_delay_seconds=0),
    )

    assert result == "ok"
    assert retry_count == 2


@pytest.mark.asyncio
async def test_ai_service_enforces_provider_timeout() -> None:
    service = AIService(
        providers=[SlowAIProvider()],
        config=AIConfig(provider="mock", request_timeout_seconds=0.001),
        retry_policy=RetryPolicy(max_attempts=1, base_delay_seconds=0),
    )
    article = ArticleAIInput(title="AI chip launch", content="A company launched a new AI accelerator.")

    with pytest.raises(AIProviderTimeout):
        await service.enrich_article(article)


def test_cost_calculation_uses_model_pricing() -> None:
    cost = calculate_cost_usd(
        "gpt-4o-mini",
        TokenUsage(prompt_tokens=1_000_000, completion_tokens=500_000),
    )

    assert cost == Decimal("0.450000")


def test_ai_service_clips_input_before_provider_request() -> None:
    service = AIService(providers=[MockAIProvider()], config=AIConfig(provider="mock", max_input_chars=10))
    article = ArticleAIInput(title="AI chip launch", content="x" * 50)

    clipped = service._clip_article(article)

    assert clipped.content == "x" * 10


def test_enrichment_input_fingerprint_changes_with_prompt_version() -> None:
    base = build_enrichment_input_fingerprint(
        title="Same article",
        content="Same content",
        prompt_version="summary_v1",
        provider="openai",
        model="gpt-4o-mini",
    )
    changed_prompt = build_enrichment_input_fingerprint(
        title="Same article",
        content="Same content",
        prompt_version="summary_v2",
        provider="openai",
        model="gpt-4o-mini",
    )

    assert len(base) == 64
    assert base != changed_prompt
