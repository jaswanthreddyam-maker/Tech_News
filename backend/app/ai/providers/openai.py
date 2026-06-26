import json
import time
from functools import cached_property

import httpx
import openai
from openai import AsyncOpenAI

from app.ai.exceptions import (
    AIProviderError,
    AIProviderNotConfigured,
    AIProviderTimeout,
)
from app.ai.providers.base import BaseAIProvider
from app.ai.schemas import AIProviderResponse, AITaskRequest, TokenUsage


class OpenAIProvider(BaseAIProvider):
    provider_name = "openai"
    default_model = "gpt-4o-mini"
    response_format = "json_object"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    @property
    def sdk_version(self) -> str | None:
        return getattr(openai, "__version__", None)

    @cached_property
    def client(self) -> AsyncOpenAI:
        if not self.api_key:
            raise AIProviderNotConfigured("OpenAI API key is missing.")
        return AsyncOpenAI(api_key=self.api_key)

    async def summarize(self, request: AITaskRequest) -> AIProviderResponse:
        return await self._call_api(request)

    async def generate_keywords(self, request: AITaskRequest) -> AIProviderResponse:
        return await self._call_api(request)

    async def generate_tags(self, request: AITaskRequest) -> AIProviderResponse:
        return await self._call_api(request)

    async def analyze_sentiment(self, request: AITaskRequest) -> AIProviderResponse:
        return await self._call_api(request)

    async def _call_api(self, request: AITaskRequest) -> AIProviderResponse:
        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=[
                    {"role": "system", "content": request.prompt},
                    {"role": "user", "content": request.article.content},
                ],
                max_tokens=request.max_output_tokens,
                response_format={"type": "json_object"},
            )
        except openai.AuthenticationError as exc:
            # Note: We let caller handle disabling or logging.
            raise AIProviderError("Authentication error with OpenAI") from exc
        except openai.RateLimitError as exc:
            raise AIProviderError("OpenAI rate limit exceeded") from exc
        except (openai.APITimeoutError, httpx.TimeoutException) as exc:
            raise AIProviderTimeout("OpenAI API timeout") from exc
        except (openai.APIConnectionError, httpx.NetworkError) as exc:
            raise AIProviderError("Network error connecting to OpenAI") from exc
        except openai.OpenAIError as exc:
            raise AIProviderError(f"OpenAI API error: {exc}") from exc

        latency_ms = int((time.time() - start_time) * 1000)

        # Parse usage
        prompt_tokens = 0
        completion_tokens = 0
        if response.usage:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

        # Parse JSON payload
        try:
            content = response.choices[0].message.content or "{}"
            payload = json.loads(content)
        except (json.JSONDecodeError, IndexError, AttributeError) as exc:
            raise AIProviderError("Failed to parse JSON response from OpenAI") from exc

        return AIProviderResponse(
            provider=self.provider_name,
            model=request.model,
            task_type=request.task_type,
            payload=payload,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ),
            latency_ms=latency_ms,
            prompt_hash=request.prompt_hash,
        )
