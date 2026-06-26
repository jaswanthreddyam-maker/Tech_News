from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class WorkingMemoryFrame(BaseModel):
    """
    Immutable ephemeral state attached to a WorkflowContext.
    Aligns with ADR-0036 (Workflow Context Is Immutable).
    """
    frame_id: str
    parent_frame_id: str | None = None
    workflow_id: str
    snapshot_id: int
    budget_remaining: dict[str, Any]
    variables: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
