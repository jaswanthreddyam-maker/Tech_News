from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GoalState(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    REFLECTING = "REFLECTING"
    EVALUATING = "EVALUATING"
    ADAPTING = "ADAPTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"

class Goal(BaseModel):
    """
    Autonomous agent execution intent (ADR-0063).
    """
    goal_id: str
    owner_id: str # Agent or User
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str | None = None
    state: GoalState = GoalState.CREATED
    current_workflow_id: str | None = None
    reflection_artifacts: list[str] = Field(default_factory=list)
    evaluation_artifacts: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
