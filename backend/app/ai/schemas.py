from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AITaskType(str, Enum):
    SUMMARY = "summary"
    KEYWORDS = "keywords"
    TAGS = "tags"
    SENTIMENT = "sentiment"
    EMBEDDING = "embedding"
    ENTITIES = "entities"
    TOPICS = "topics"
    TIMELINE = "timeline"
    RELATIONSHIPS = "relationships"


class AIJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    FALLBACK = "fallback"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ArticleAIInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    source: str | None = None
    source_url: str | None = None


class AITaskRequest(BaseModel):
    task_type: AITaskType
    article: ArticleAIInput
    prompt: str
    prompt_version: str
    prompt_hash: str
    model: str
    max_output_tokens: int


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    @field_validator("total_tokens")
    @classmethod
    def total_matches_parts(cls, value: int, info: Any) -> int:
        prompt_tokens = info.data.get("prompt_tokens", 0)
        completion_tokens = info.data.get("completion_tokens", 0)
        expected_total = prompt_tokens + completion_tokens
        if value == 0 and expected_total > 0:
            return expected_total
        return value


class AIProviderResponse(BaseModel):
    provider: str
    model: str
    task_type: AITaskType
    payload: dict[str, Any]
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int = Field(default=0, ge=0)
    cache_hit: bool = False
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    enrichment_input_fingerprint: str | None = None
    prompt_hash: str | None = None


class SummaryOutput(BaseModel):
    summary: str = Field(..., min_length=1, max_length=1200)


class KeywordsOutput(BaseModel):
    keywords: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, value: list[str]) -> list[str]:
        return _clean_unique(value, limit=20)


class TagsOutput(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value: list[str]) -> list[str]:
        return _clean_unique(value, limit=12)


class SentimentOutput(BaseModel):
    sentiment: SentimentLabel


class AIEnrichmentOutput(BaseModel):
    summary: str = Field(..., min_length=1, max_length=1200)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=12)
    sentiment: SentimentLabel = SentimentLabel.NEUTRAL

    @field_validator("keywords")
    @classmethod
    def clean_enrichment_keywords(cls, value: list[str]) -> list[str]:
        return _clean_unique(value, limit=20)

    @field_validator("tags")
    @classmethod
    def clean_enrichment_tags(cls, value: list[str]) -> list[str]:
        return _clean_unique(value, limit=12)


class AITelemetryRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    provider: str
    model: str
    task_type: AITaskType
    prompt_version: str
    prompt_hash: str | None = None
    status: AIJobStatus
    latency_ms: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cost_usd: Decimal = Decimal("0")
    cache_hit: bool = False
    retry_count: int = Field(default=0, ge=0)
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    enrichment_input_fingerprint: str | None = Field(default=None, min_length=64, max_length=64)


class AIServiceResult(BaseModel):
    output: AIEnrichmentOutput
    status: AIJobStatus
    telemetry: list[AITelemetryRecord] = Field(default_factory=list)
    error: str | None = None


def _clean_unique(values: list[str], limit: int) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        normalized = " ".join(item.strip().split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
        if len(cleaned) >= limit:
            break
    return cleaned
