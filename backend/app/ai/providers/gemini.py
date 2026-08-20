import asyncio
import json
import time

from app.ai.exceptions import (
    AIProviderError,
    AIProviderNotConfigured,
    AIProviderTimeout,
)
from app.ai.providers.base import BaseAIProvider
from app.ai.schemas import AIProviderResponse, AITaskRequest, TokenUsage
from app.core.config import settings


class GeminiProvider(BaseAIProvider):
    provider_name = "gemini"
    default_model = "gemini-2.5-flash"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)

    def _get_client(self):
        if not self.api_key or self.api_key in ("mock-happy-path", ""):
            raise AIProviderNotConfigured("GEMINI_API_KEY is not set or is a placeholder.")
        from openai import AsyncOpenAI
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            timeout=10.0,
        )

    async def _call_api(self, request: AITaskRequest) -> AIProviderResponse:
        client = self._get_client()
        start_time = time.time()

        prompt_text = f"{request.prompt}\n\nArticle:\n{request.article.content}"

        try:
            response = await client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "user", "content": prompt_text}
                ],
                response_format={"type": "json_object"},
                max_tokens=request.max_output_tokens,
                temperature=0.3,
            )
        except Exception as exc:
            err_str = str(exc).lower()
            if "timeout" in err_str or "deadline" in err_str:
                raise AIProviderTimeout(f"Gemini API timeout: {exc}") from exc
            if any(k in err_str for k in ("permission", "api_key", "unauthenticated", "invalid", "auth")):
                raise AIProviderError(f"Gemini auth error: {exc}") from exc
            raise AIProviderError(f"Gemini API error: {exc}") from exc

        latency_ms = int((time.time() - start_time) * 1000)

        raw_text = response.choices[0].message.content or "{}"
        try:
            # Strip markdown code fences if Gemini wraps the JSON
            if "```" in raw_text:
                parts = raw_text.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    try:
                        payload = json.loads(part)
                        break
                    except json.JSONDecodeError:
                        continue
                else:
                    payload = json.loads(raw_text.strip())
            else:
                payload = json.loads(raw_text.strip())
        except (json.JSONDecodeError, AttributeError) as exc:
            raise AIProviderError(f"Failed to parse Gemini JSON response: {exc}") from exc

        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0

        return AIProviderResponse(
            provider=self.provider_name,
            model=self.default_model,
            task_type=request.task_type,
            payload=payload,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            ),
            latency_ms=latency_ms,
            prompt_hash=request.prompt_hash,
        )

    async def summarize(self, request: AITaskRequest) -> AIProviderResponse:
        return await self._call_api(request)

    async def generate_keywords(self, request: AITaskRequest) -> AIProviderResponse:
        return await self._call_api(request)

    async def generate_tags(self, request: AITaskRequest) -> AIProviderResponse:
        return await self._call_api(request)

    async def analyze_sentiment(self, request: AITaskRequest) -> AIProviderResponse:
        return await self._call_api(request)
