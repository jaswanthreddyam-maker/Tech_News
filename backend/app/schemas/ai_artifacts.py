from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AIArtifactStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"

class ArtifactLineage(BaseModel):
    derived_from: list[int] = Field(default_factory=list)
    depends_on: list[int] = Field(default_factory=list)
    supersedes: int | None = None
    generated_by: str
    snapshot_id: int

class AIArtifactMetadata(BaseModel):
    artifact_id: int | None = None
    version: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: AIArtifactStatus = AIArtifactStatus.CREATED
    confidence: float
    context_version: str
    model_version: str
    prompt_version: str
    lineage: ArtifactLineage | None = None

class BaseAIArtifact(BaseModel):
    metadata: AIArtifactMetadata
    # Subclasses define specific payload fields

class TemporalPrecision(str, Enum):
    YEAR = "YEAR"
    MONTH = "MONTH"
    DAY = "DAY"
    HOUR = "HOUR"
    UNKNOWN = "UNKNOWN"

class TimelineEvent(BaseModel):
    event_id: str
    start_time: str
    end_time: str | None = None
    precision: TemporalPrecision
    title: str
    description: str
    confidence: float
    citations: list[str]
    entities: list[str]
    importance: float

class TimelineArtifact(BaseAIArtifact):
    events: list[TimelineEvent]

class ReflectionArtifact(BaseAIArtifact):
    reflection_type: str  # MEMORY, WORKFLOW, ARTIFACT, GRAPH, RECOMMENDATION
    subject_type: str     # PLANNER, CAPABILITY, ARTIFACT, MEMORY_INDEX, etc.
    subject_id: str
    workflow_id: str
    severity: str         # INFO, WARNING, CRITICAL
    findings: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    approval_state: str = "PENDING"

class EvaluationArtifact(BaseAIArtifact):
    metric: str
    score: float
    benchmark: str
    expected_answer: str | None = None
    actual_answer: str | None = None
    failure_reasons: list[str] = Field(default_factory=list)
