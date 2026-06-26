from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from app.ai.config import AIConfig
from app.ai.exceptions import AIProviderError, AIProviderTimeout
from app.ai.providers.openai import OpenAIProvider
from app.ai.schemas import AIJobStatus, AITaskRequest, AITaskType, ArticleAIInput
from app.ai.service import AIService
from app.core.config import settings


def make_mock_response(content: str, prompt_tokens: int = 10, completion_tokens: int = 20) -> ChatCompletion:
    return ChatCompletion(
        id="chatcmpl-123",
        choices=[
            Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content=content, role="assistant"))
        ],
        created=1677652288,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=CompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


@pytest.fixture
def request_payload() -> AITaskRequest:
    return AITaskRequest(
        task_type=AITaskType.SUMMARY,
        article=ArticleAIInput(title="Test", content="Test Content"),
        prompt="Summarize this",
        prompt_version="v1",
        prompt_hash="dummy_hash",
        model="gpt-4o-mini",
        max_output_tokens=100,
    )


@pytest.mark.asyncio
async def test_openai_provider_parses_json_and_usage(request_payload: AITaskRequest):
    provider = OpenAIProvider(api_key="dummy")

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = make_mock_response('{"summary": "Test summary"}')

    with patch.object(provider, "client", new=mock_client):
        response = await provider.summarize(request_payload)

    assert response.payload == {"summary": "Test summary"}
    assert response.usage.prompt_tokens == 10
    assert response.usage.completion_tokens == 20
    assert response.provider == "openai"
    mock_client.chat.completions.create.assert_called_once()
    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_openai_provider_raises_validation_error_on_invalid_json(request_payload: AITaskRequest):
    provider = OpenAIProvider(api_key="dummy")
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = make_mock_response("invalid json")

    with patch.object(provider, "client", new=mock_client):
        with pytest.raises(AIProviderError, match="Failed to parse JSON response"):
            await provider.summarize(request_payload)


@pytest.mark.asyncio
async def test_openai_provider_maps_exceptions(request_payload: AITaskRequest):
    provider = OpenAIProvider(api_key="dummy")
    mock_client = AsyncMock()

    # Test Timeout
    mock_client.chat.completions.create.side_effect = openai.APITimeoutError(request=MagicMock())
    with patch.object(provider, "client", new=mock_client):
        with pytest.raises(AIProviderTimeout):
            await provider.summarize(request_payload)

    # Test Rate Limit
    mock_client.chat.completions.create.side_effect = openai.RateLimitError(
        message="Rate limit", response=MagicMock(), body=None
    )
    with patch.object(provider, "client", new=mock_client):
        with pytest.raises(AIProviderError, match="rate limit"):
            await provider.summarize(request_payload)


@pytest.mark.asyncio
async def test_ai_service_end_to_end_caching_with_provider():
    # Test cache miss -> populate -> cache hit
    provider = OpenAIProvider(api_key="dummy")
    mock_client = AsyncMock()

    mock_client.chat.completions.create.side_effect = [
        make_mock_response('{"summary": "Cached"}'),
        make_mock_response('{"keywords": ["cache"]}'),
        make_mock_response('{"tags": ["cache-tag"]}'),
        make_mock_response('{"sentiment": "positive"}'),
        # Should not be called on cache hit
        make_mock_response('{"summary": "Not Cached"}'),
        make_mock_response('{"keywords": []}'),
        make_mock_response('{"tags": []}'),
        make_mock_response('{"sentiment": "neutral"}'),
    ]

    # Override cached property
    provider.__dict__["client"] = mock_client

    config = AIConfig(provider="openai")
    service = AIService(providers=[provider], config=config)
    article = ArticleAIInput(title="Cache test", content="Content")

    # Call 1 (Cache Miss)
    result1 = await service.enrich_article(article)
    assert result1.status == AIJobStatus.COMPLETED
    assert result1.output.summary == "Cached"
    assert result1.telemetry[0].provider_metadata == {
        "provider": "openai",
        "model": config.summary_model,
        "prompt_version": "summary_v1",
        "prompt_hash": "f3ba0efe3adab24cb88fa89f18188c3656edd3351a49cb307e0091482faf60ea",
        "sdk_version": openai.__version__,
        "response_format": "json_object",
    }

    # Verify provider was called 4 times (summary, keywords, tags, sentiment)
    assert mock_client.chat.completions.create.call_count == 4

    # Call 2 (Cache Hit)
    result2 = await service.enrich_article(article)
    assert result2.status == AIJobStatus.COMPLETED
    assert result2.output.summary == "Cached"  # Should still be "Cached"
    assert result2.telemetry[0].cache_hit is True
    assert result2.telemetry[0].provider_metadata["sdk_version"] == openai.__version__

    # Verify provider was NOT called again
    assert mock_client.chat.completions.create.call_count == 4


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-place"), reason="Real OPENAI_API_KEY not set"
)
async def test_live_openai_provider_integration():
    provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY)
    request = AITaskRequest(
        task_type=AITaskType.SUMMARY,
        article=ArticleAIInput(title="Test", content="The integration test was successful."),
        prompt="Summarize this in JSON with a 'summary' key.",
        prompt_version="v1",
        model="gpt-4o-mini",
        max_output_tokens=100,
    )
    response = await provider.summarize(request)
    assert response.provider == "openai"
    assert "summary" in response.payload
    assert response.usage.total_tokens > 0
