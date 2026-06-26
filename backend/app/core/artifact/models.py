from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ArtifactStatus(str, Enum):
    """
    ADR-0077: Strict state machine for Artifact generation.
    """
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"

class ArtifactMetadata(BaseModel):
    version: str
    published_at: datetime | None = None
    published_by: str | None = None
    source_goal: str | None = None
    workspace_snapshot: str | None = None
    configuration_version: str | None = None

class Artifact(BaseModel):
    artifact_id: str
    status: ArtifactStatus = ArtifactStatus.GENERATING
    metadata: ArtifactMetadata
    content: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
