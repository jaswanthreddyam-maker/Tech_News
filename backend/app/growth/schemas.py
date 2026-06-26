from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeatureFlagContext(BaseModel):
    """
    The canonical execution context for evaluating feature flags.
    Provides all necessary dimensions for targeting rules.
    """
    user_id: str | None = None
    session_id: str | None = None
    country: str | None = None
    language: str | None = None
    organization: str | None = None
    device: str | None = None
    app_version: str | None = None
    environment: str = Field(..., description="e.g., 'development', 'staging', 'production'")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EvaluationTrace(BaseModel):
    environment: str
    rule_name: str
    rule_version: str
    priority: int
    matched: bool
    execution_time_ms: float


class FeatureFlagEvaluation(BaseModel):
    """
    The result of evaluating a feature flag.
    """
    flag_key: str
    value: Any
    reason: str
    trace: list[EvaluationTrace] = Field(default_factory=list)
    evaluation_version: str = "v1"


class RuleSchema(BaseModel):
    """
    Base schema for rule definitions stored in the database.
    """
    rule_type: str
    rule_id: str
    priority: int = 100
    rule_version: str = "1.0"
    config: dict[str, Any]


class FeatureFlagCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    default_value: Any
    environment_states: dict[str, bool] = Field(default_factory=dict)
    rules: list[RuleSchema] = Field(default_factory=list)


class FeatureFlagResponse(FeatureFlagCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExperimentVariantSchema(BaseModel):
    key: str
    name: str
    weight: int
    version: str = "v1"
    config: dict[str, Any]

class ExperimentVariantResponse(ExperimentVariantSchema):
    id: int

    class Config:
        from_attributes = True

class ExperimentCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    status: str = "DRAFT"
    subject_type: str = "USER"
    assignment_strategy: str = "HASH"
    allocation_percentage: int = 100
    mutual_exclusion_group_id: str | None = None
    environment_states: dict[str, bool] = Field(default_factory=dict)
    rules: list[RuleSchema] = Field(default_factory=list)

class ExperimentResponse(ExperimentCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    variants: list[ExperimentVariantResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

class ExperimentAssignmentSchema(BaseModel):
    experiment_id: int
    variant_id: int
    subject_id: str
    subject_type: str
    assignment_hash: str
    assignment_version: str
    exposure_count: int
    assigned_at: datetime
    last_exposed_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class FunnelStepSchema(BaseModel):
    step_order: int
    name: str
    event_matcher: dict[str, Any]
    is_optional: bool = False

class FunnelStepResponse(FunnelStepSchema):
    id: int
    funnel_id: int

    class Config:
        from_attributes = True

class FunnelCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    version: str = "v1"
    status: str = "DRAFT"
    subject_type: str = "USER"
    time_window_seconds: int | None = None
    steps: list[FunnelStepSchema] = Field(default_factory=list)

class FunnelResponse(FunnelCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    steps: list[FunnelStepResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

class FunnelMetricsResponse(BaseModel):
    funnel_id: int
    time_bucket: datetime
    dimension_key: str
    total_started: int
    total_completed: int
    step_counts: dict[str, int]
    conversion_rate: float
    dropoff_rate: float

    class Config:
        from_attributes = True

class CohortRuleSchema(BaseModel):
    rule_capability: str
    expression: dict[str, Any]

class CohortCreate(BaseModel):
    key: str
    name: str
    description: str | None = None
    version: str = "v1"
    status: str = "DRAFT"
    subject_type: str = "USER"
    refresh_mode: str = "REAL_TIME"
    parent_cohort_id: int | None = None
    rules: list[CohortRuleSchema] = Field(default_factory=list)

class CohortResponse(CohortCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CohortMembershipResponse(BaseModel):
    id: int
    cohort_id: int
    subject_id: str
    status: str
    reason: str | None = None
    added_at: datetime
    removed_at: datetime | None = None

    class Config:
        from_attributes = True

class CohortStatsResponse(BaseModel):
    cohort_id: int
    total_members: int
    active_members: int
    paused_members: int

class CohortSnapshotResponse(BaseModel):
    id: int
    cohort_id: int
    snapshot_time: datetime
    member_count: int
    entered: int
    exited: int
    growth_rate: float
    metrics: dict[str, Any]

    class Config:
        from_attributes = True
