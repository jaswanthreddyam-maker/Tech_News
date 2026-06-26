from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    ONLINE = "ONLINE"
    DELAYED = "DELAYED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


class HistorySample(BaseModel):
    timestamp: str = Field(..., description="ISO 8601 formatted UTC check timestamp")
    status: HealthStatus
    latency_ms: float


class HealthSnapshot(BaseModel):
    service: str = Field(..., description="Target service name (e.g. postgres, redis, worker, beat, queue, nginx)")
    status: HealthStatus
    available: bool = Field(True, description="Service availability flag")
    status_reason: str | None = Field(None, description="Detailed reason for current status")
    latency_ms: float
    last_checked: str = Field(..., description="ISO 8601 formatted UTC timestamp of last attempt")
    last_success: str | None = Field(None, description="ISO 8601 formatted UTC timestamp of last success")
    heartbeat_age_ms: float | None = Field(None, description="Age of last heartbeat in ms")
    ttl_remaining: float | None = Field(None, description="Remaining TTL in ms")
    collector_version: int = Field(2, description="Telemetry collector version")
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


from typing import Generic, TypeVar

T = TypeVar("T")


class TelemetryMetadata(BaseModel):
    schema_version: int = Field(2, description="Monitoring payload schema version")
    collector_version: int = Field(2, description="Telemetry collector version")
    generated_at: str = Field(..., description="ISO 8601 formatted generation time")
    hostname: str | None = None
    git_sha: str | None = None
    build: str | None = None


class VersionedTelemetryEnvelope(BaseModel, Generic[T]):
    schema_version: int = Field(2, description="Monitoring payload schema version")
    generated_at: str = Field(..., description="ISO 8601 formatted generation time")
    meta_info: TelemetryMetadata | None = Field(None, alias="_meta")
    data: T


class SourceHealth(BaseModel):
    total: int
    healthy: int
    degraded: int
    failed: int


class ArticlePipeline(BaseModel):
    raw: int
    processed: int
    published: int
    draft: int
    rejected: int


class AIQueueMetrics(BaseModel):
    queued: int
    processing: int
    completed: int
    failed: int
    retry: int


class OverviewResponse(BaseModel):
    generated_at: str
    source_health: SourceHealth
    article_pipeline: ArticlePipeline
    ai_queue: AIQueueMetrics
    emergency_cutoff_active: bool
    error: str | None = None
    stale: bool | None = None


class HealthScorePayload(BaseModel):
    score: int
    grade: str
    calculated_at: str | None = None


class InfrastructureResponse(BaseModel):
    health_score: HealthScorePayload
    services: dict[str, Any]


# Telemetry V3 Schemas


class MetricValue(BaseModel, Generic[T]):
    value: T
    source: str
    updated_at: str
    window: str


class CurrentStateSnapshot(BaseModel):
    queue_depth: MetricValue[int]
    active_workers: MetricValue[int]
    active_crawlers: MetricValue[int]
    ai_queue: MetricValue[int]


class ThroughputSnapshot(BaseModel):
    ingestion_rate_sec: MetricValue[float]


class HistoricalCounts(BaseModel):
    discovered: int
    queued: int
    fetched: int
    filtered: int
    deduplicated: int
    processed: int
    published: int
    failed: int


class HistoricalSnapshot(BaseModel):
    all_time: HistoricalCounts
    last_24h: HistoricalCounts


class QualitySnapshot(BaseModel):
    thumbnail_coverage: MetricValue[float]
    average_resolution: MetricValue[float]
    broken_images: MetricValue[int]
    fallback_usage: MetricValue[int]
    thumbnail_source_distribution: MetricValue[dict[str, int]]
    average_ranking_score: MetricValue[float]


class AISnapshot(BaseModel):
    enabled: bool
    provider_name: str
    provider_model: str
    healthy: bool
    success_rate: MetricValue[float]
    fallback_rate: MetricValue[float]
    cost_usd_today: MetricValue[float]
    tokens_total: MetricValue[int]
    average_latency_p95: MetricValue[float]


class RankingSnapshot(BaseModel):
    enabled: bool
    last_run: str | None
    articles_evaluated: MetricValue[int]
    active_articles: MetricValue[int]
    expired_articles: MetricValue[int]


class ArtifactTelemetrySnapshot(BaseModel):
    artifact_generation_time_p95: MetricValue[float]
    artifact_storage_time_p95: MetricValue[float]
    artifact_cache_time_p95: MetricValue[float]
    artifact_lookup_time_p95: MetricValue[float]
    entity_link_time_p95: MetricValue[float]
    graph_lookup_time_p95: MetricValue[float]
    graph_merge_time_p95: MetricValue[float]
    validation_time_p95: MetricValue[float]
    cache_hit_rate: MetricValue[float]
    cache_invalidations: MetricValue[int]

class GraphEvolutionTelemetrySnapshot(BaseModel):
    average_confidence: MetricValue[float]
    alias_resolution_success_rate: MetricValue[float]
    average_merge_confidence: MetricValue[float]
    conflict_rate: MetricValue[float]
    repair_backlog: MetricValue[int]
    graph_diameter: MetricValue[int]
    average_node_degree: MetricValue[float]
    traversal_latency_p95: MetricValue[float]
    merge_candidates_generated: MetricValue[int]
    auto_merges_executed: MetricValue[int]
    manual_reviews_flagged: MetricValue[int]

class ResearchEngineTelemetrySnapshot(BaseModel):
    intent_distribution: MetricValue[dict[str, int]]
    average_graph_depth: MetricValue[float]
    average_evidence_count: MetricValue[float]
    planner_cache_hit_rate: MetricValue[float]
    snapshot_cache_hit_rate: MetricValue[float]
    retrieval_cache_hit_rate: MetricValue[float]
    provider_failures: MetricValue[int]
    validation_failures: MetricValue[int]
    average_token_cost: MetricValue[float]
    average_graph_size: MetricValue[int]
    average_artifact_count: MetricValue[int]

class PipelineTelemetrySnapshot(BaseModel):
    current_state: CurrentStateSnapshot
    throughput: ThroughputSnapshot
    quality: QualitySnapshot
    historical: HistoricalSnapshot
    ai_engine: AISnapshot
    ranking_engine: RankingSnapshot
    artifact_engine: ArtifactTelemetrySnapshot | None = None
    graph_evolution: GraphEvolutionTelemetrySnapshot | None = None
    research_engine: ResearchEngineTelemetrySnapshot | None = None
    semantic_metrics: dict[str, Any] | None = None
    # Deprecated v2 lifecycle
    lifecycle_states: dict[str, int] | None = Field(None, description="Deprecated for RC1 compatibility")

    meta_info: dict[str, Any] = Field(default_factory=lambda: {"schema_version": 3}, alias="_meta")
