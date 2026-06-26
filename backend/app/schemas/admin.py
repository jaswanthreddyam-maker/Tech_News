from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    title: str | None = None
    message: str | None = None
    created_at: str | None = None
    read_at: str | None = None


class AIJobHistoryResponse(BaseModel):
    id: int
    raw_article_id: int | None = None
    processed_article_id: int | None = None
    status: str
    provider: str
    model_name: str
    task_type: str | None = None
    prompt_version: str | None = None
    tokens_prompt: int
    tokens_completion: int
    total_tokens: int | None = None
    cost_usd: float
    latency_ms: int | None = None
    cache_hit: bool | None = None
    error_message: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread: int


class CostAggregationBreakdown(BaseModel):
    model: str
    cost: float
    jobs_count: int


class CostAggregationTotals(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost_usd: float


class AI_CostAggregationResponse(BaseModel):
    aggregated: CostAggregationTotals
    models_breakdown: list[CostAggregationBreakdown]
