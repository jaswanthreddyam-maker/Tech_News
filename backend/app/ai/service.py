import asyncio
import hashlib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.ai.cache import MemoryAICache
from app.ai.circuit_breaker import CircuitBreaker
from app.ai.config import AIConfig
from app.ai.cost import calculate_cost_usd
from app.ai.enforcement import AIBudgetEnforcer, AIRateLimiter
from app.ai.exceptions import AIError, AIPromptError, AIProviderError, AIProviderTimeout, AIResponseValidationError
from app.ai.fingerprint import build_enrichment_input_fingerprint
from app.ai.providers.base import BaseAIProvider
from app.ai.providers.factory import build_ai_provider
from app.ai.retry import RetryPolicy, retry_async
from app.ai.schemas import (
    AIEnrichmentOutput,
    AIJobStatus,
    AIProviderResponse,
    AIServiceResult,
    AITaskRequest,
    AITaskType,
    ArticleAIInput,
    KeywordsOutput,
    SentimentOutput,
    SummaryOutput,
    TagsOutput,
)
from app.ai.telemetry import telemetry_from_response
from app.core.redis import get_redis_client


class PromptRegistry:
    def __init__(self, prompt_dir: Path | None = None) -> None:
        self.prompt_dir = prompt_dir or Path(__file__).parent / "prompts"
        self._cache: dict[str, tuple[str, str]] = {}  # version -> (content, hash)

    def get_prompt(self, prompt_version: str) -> tuple[str, str]:
        """Returns (prompt_content, sha256_hash)"""
        if prompt_version in self._cache:
            return self._cache[prompt_version]

        prompt_path = self.prompt_dir / f"{prompt_version}.md"
        if not prompt_path.exists():
            raise AIPromptError(f"Prompt template not found: {prompt_version}")

        content = prompt_path.read_text(encoding="utf-8").strip()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        self._cache[prompt_version] = (content, content_hash)
        return content, content_hash


class AIService:
    def __init__(
        self,
        *,
        providers: list[BaseAIProvider] | None = None,
        config: AIConfig | None = None,
        prompt_registry: PromptRegistry | None = None,
        cache: MemoryAICache | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.config = config or AIConfig()
        if providers:
            self.providers = providers
        else:
            self.providers = [build_ai_provider(p) for p in self.config.providers]
        self.prompt_registry = prompt_registry or PromptRegistry()
        self.cache = cache or MemoryAICache()
        self.retry_policy = retry_policy or RetryPolicy(max_attempts=self.config.max_retries)

    async def enrich_article(
        self,
        article: ArticleAIInput,
        *,
        fallback: AIEnrichmentOutput | None = None,
    ) -> AIServiceResult:
        clipped_article = self._clip_article(article)
        telemetry = []

        try:
            summary_response, summary_retries = await self._run_task(AITaskType.SUMMARY, clipped_article)
            keywords_response, keyword_retries = await self._run_task(AITaskType.KEYWORDS, clipped_article)
            tags_response, tag_retries = await self._run_task(AITaskType.TAGS, clipped_article)
            sentiment_response, sentiment_retries = await self._run_task(AITaskType.SENTIMENT, clipped_article)

            responses_with_retries = [
                (summary_response, summary_retries),
                (keywords_response, keyword_retries),
                (tags_response, tag_retries),
                (sentiment_response, sentiment_retries),
            ]
            telemetry.extend(
                telemetry_from_response(
                    response,
                    prompt_version=self.config.prompt_version_for(response.task_type),
                    retry_count=retry_count,
                )
                for response, retry_count in responses_with_retries
            )

            summary = self._validate_payload(SummaryOutput, summary_response.payload)
            keywords = self._validate_payload(KeywordsOutput, keywords_response.payload)
            tags = self._validate_payload(TagsOutput, tags_response.payload)
            sentiment = self._validate_payload(SentimentOutput, sentiment_response.payload)

            return AIServiceResult(
                output=AIEnrichmentOutput(
                    summary=summary.summary,
                    keywords=keywords.keywords,
                    tags=tags.tags,
                    sentiment=sentiment.sentiment,
                ),
                status=AIJobStatus.COMPLETED,
                telemetry=telemetry,
            )
        except AIError as exc:
            if fallback is None:
                raise
            telemetry = [
                record.model_copy(update={"status": AIJobStatus.FALLBACK, "error": str(exc)}) for record in telemetry
            ]
            return AIServiceResult(output=fallback, status=AIJobStatus.FALLBACK, telemetry=telemetry, error=str(exc))

    async def _run_task(self, task_type: AITaskType, article: ArticleAIInput) -> tuple[AIProviderResponse, int]:
        prompt_version = self.config.prompt_version_for(task_type)
        prompt, prompt_hash = self.prompt_registry.get_prompt(prompt_version)
        request = AITaskRequest(
            task_type=task_type,
            article=article,
            prompt=prompt,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            model=self.config.summary_model,
            max_output_tokens=self.config.max_output_tokens,
        )

        redis_client = get_redis_client()
        budget_enforcer = AIBudgetEnforcer(redis_client, daily_limit=5.0)
        rate_limiter = AIRateLimiter(redis_client, max_requests_per_second=5)

        last_exc: Exception | None = None
        for provider in self.providers:
            circuit_breaker = CircuitBreaker(redis_client, provider.provider_name)

            if not await circuit_breaker.can_execute():
                last_exc = AIProviderError(f"Circuit breaker open for {provider.provider_name}")
                continue

            if not await budget_enforcer.check_budget():
                raise AIError("Daily AI budget exceeded")

            provider_metadata = provider.provider_metadata_for(request)
            enrichment_input_fingerprint = build_enrichment_input_fingerprint(
                title=article.title,
                content=article.content,
                prompt_version=prompt_version,
                provider=provider.provider_name,
                model=request.model,
            )

            cache_key = self.cache.build_key(
                provider=provider.provider_name,
                model=request.model,
                task_type=task_type.value,
                prompt_version=prompt_version,
                title=article.title,
                content=article.content,
            )
            cached_payload = self.cache.get(cache_key)
            if cached_payload is not None:
                return (
                    AIProviderResponse(
                        provider=provider.provider_name,
                        model=request.model,
                        task_type=task_type,
                        payload=cached_payload,
                        cache_hit=True,
                        provider_metadata=provider_metadata,
                        enrichment_input_fingerprint=enrichment_input_fingerprint,
                        prompt_hash=prompt_hash,
                    ),
                    0,
                )

            async def operation(
                provider=provider,
                circuit_breaker=circuit_breaker,
                provider_metadata=provider_metadata,
                enrichment_input_fingerprint=enrichment_input_fingerprint,
                cache_key=cache_key,
            ) -> AIProviderResponse:
                if not await rate_limiter.acquire():
                    raise AIProviderError("Rate limit exceeded")
                try:
                    response = await asyncio.wait_for(
                        self._dispatch(provider, request),
                        timeout=self.config.request_timeout_seconds,
                    )
                except TimeoutError as exc:
                    await circuit_breaker.record_failure()
                    raise AIProviderTimeout(f"AI task timed out after {self.config.request_timeout_seconds}s") from exc
                except Exception:
                    await circuit_breaker.record_failure()
                    raise

                await circuit_breaker.record_success()
                response = response.model_copy(
                    update={
                        "provider_metadata": provider_metadata,
                        "enrichment_input_fingerprint": enrichment_input_fingerprint,
                    }
                )
                self.cache.set(cache_key, response.payload)
                return response

            try:
                response, retries = await retry_async(operation, policy=self.retry_policy)
                cost = calculate_cost_usd(request.model, response.usage)
                await budget_enforcer.increment_spend(cost)
                return response, retries
            except Exception as exc:
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        raise AIError("No AI providers available")

    async def extract_entities(self, article: ArticleAIInput) -> list[dict]:
        """
        Extract named entities (companies, products, people) from article content.
        Returns a list of entity dicts on success, or [] on failure/disabled.
        """
        clipped = self._clip_article(article)
        try:
            response, _ = await self._run_task(AITaskType.ENTITIES, clipped)
            payload = response.payload
            # Normalise: accept either {"entities": [...]} or a bare list
            if isinstance(payload, list):
                return payload
            return payload.get("entities", [])
        except Exception as exc:
            import logging
            logging.getLogger("tech_news.ai_service").warning(
                f"Entity extraction failed for '{article.title[:50]}': {exc}"
            )
            return []

    async def extract_topics(self, article: ArticleAIInput) -> list[dict]:
        """
        Classify topics for article content.
        Returns a list of topic dicts on success, or [] on failure/disabled.
        """
        clipped = self._clip_article(article)
        try:
            response, _ = await self._run_task(AITaskType.TOPICS, clipped)
            payload = response.payload
            if isinstance(payload, list):
                return payload
            return payload.get("topics", [])
        except Exception as exc:
            import logging
            logging.getLogger("tech_news.ai_service").warning(
                f"Topic classification failed for '{article.title[:50]}': {exc}"
            )
            return []

    async def _dispatch(self, provider: BaseAIProvider, request: AITaskRequest) -> AIProviderResponse:
        if request.task_type == AITaskType.SUMMARY:
            return await provider.summarize(request)
        if request.task_type == AITaskType.KEYWORDS:
            return await provider.generate_keywords(request)
        if request.task_type == AITaskType.TAGS:
            return await provider.generate_tags(request)
        if request.task_type == AITaskType.SENTIMENT:
            return await provider.analyze_sentiment(request)
        if request.task_type in (AITaskType.ENTITIES, AITaskType.TOPICS, AITaskType.TIMELINE, AITaskType.RELATIONSHIPS):
            # All knowledge-graph extraction tasks use the same generic call path
            return await provider.summarize(request)  # reuses the JSON generation flow
        raise AIResponseValidationError(f"Unsupported AI task: {request.task_type}")

    def _clip_article(self, article: ArticleAIInput) -> ArticleAIInput:
        if len(article.content) <= self.config.max_input_chars:
            return article
        return article.model_copy(update={"content": article.content[: self.config.max_input_chars]})

    def _validate_payload(self, schema: type[Any], payload: dict[str, Any]) -> Any:
        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            raise AIResponseValidationError(str(exc)) from exc
