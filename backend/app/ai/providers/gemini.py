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
        try:
            from google import genai
            return genai.Client(api_key=self.api_key)
        except ImportError as exc:
            raise AIProviderNotConfigured("google-genai package not installed.") from exc

    async def _call_api(self, request: AITaskRequest) -> AIProviderResponse:
        client = self._get_client()
        start_time = time.time()

        prompt_text = f"{request.prompt}\n\nArticle:\n{request.article.content}"

        try:
            from google import genai as _genai
            # Run synchronous SDK call in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=self.default_model,
                    contents=prompt_text,
                    config=_genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                        max_output_tokens=request.max_output_tokens,
                        temperature=0.3,
                    ),
                )
            )
        except Exception as exc:
            err_str = str(exc).lower()
            if "timeout" in err_str or "deadline" in err_str:
                raise AIProviderTimeout(f"Gemini API timeout: {exc}") from exc
            if any(k in err_str for k in ("permission", "api_key", "unauthenticated", "invalid")):
                raise AIProviderError(f"Gemini auth error: {exc}") from exc
            raise AIProviderError(f"Gemini API error: {exc}") from exc

        latency_ms = int((time.time() - start_time) * 1000)

        try:
            raw_text = response.text or "{}"
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
                    raise AIProviderError("Could not extract JSON from Gemini markdown response.")
            else:
                payload = json.loads(raw_text.strip())
        except (json.JSONDecodeError, AttributeError) as exc:
            raise AIProviderError(f"Failed to parse Gemini JSON response: {exc}") from exc

        # Extract token usage from usage_metadata if available
        usage_meta = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0

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
