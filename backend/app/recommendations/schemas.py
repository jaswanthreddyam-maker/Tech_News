from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RecommendationContext(BaseModel):
    user_id: str | None = None
    article_id: str | None = None
    topic: str | None = None
    entity: str | None = None
    language: str | None = None
    country: str | None = None
    device: str | None = None
    experiment: str | None = None
    request_time: datetime = Field(default_factory=utc_now)
    timezone: str | None = None

class RecommendationRequest(BaseModel):
    request_id: str | None = None
    context: RecommendationContext
    strategy: str
    limit: int = 10
    filters: list[str] = []
    options: dict[str, Any] = {}
    cursor: str | None = None

class RecommendationExplanation(BaseModel):
    reason: str
    weight: float
    confidence: float = 1.0
    metadata: dict[str, Any] = {}

class RecommendationCandidate(BaseModel):
    article_id: str
    score: float
    reasons: list[RecommendationExplanation] = []
    strategy: str
    features: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    debug: dict[str, Any] | None = None
    rank: int | None = None

class RecommendationTelemetry(BaseModel):
    pipeline_stage: str
    strategy: str
    candidate_count: int
    filtered_count: int
    retriever_latency_ms: float = 0.0
    validator_latency_ms: float = 0.0
    filter_latency_ms: float = 0.0
    score_latency_ms: float = 0.0
    sort_latency_ms: float = 0.0
    diversifier_latency_ms: float = 0.0
    explanation_latency_ms: float = 0.0
    postprocess_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    timestamp: datetime = Field(default_factory=utc_now)

class RecommendationResponse(BaseModel):
    request_id: str | None = None
    strategy: str
    strategy_version: str = "1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    latency_ms: float
    candidate_count: int
    candidates: list[RecommendationCandidate]
    telemetry: RecommendationTelemetry
    metadata: dict[str, Any] = {}
