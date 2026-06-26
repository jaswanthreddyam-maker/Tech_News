from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BehavioralEventPayload(BaseModel):
    event_id: str = Field(..., description="Unique UUID for this event to ensure idempotency")
    article_id: int | None = Field(None, description="The article this event relates to")
    session_id: str = Field(..., description="A unique UUID identifying the reading journey")
    event_type: str = Field(..., description="Type of event (e.g. reading_progress, article_opened)")
    event_version: str = Field(default="v1", description="Version of the event schema")
    content_version: str | None = Field(None, description="Version of the article content")
    scroll_percent: int | None = Field(None, description="Current scroll percentage")
    reading_time_seconds: int | None = Field(None, description="Accumulated active reading time")
    occurred_at: datetime = Field(..., description="When the event actually occurred on the client")
    device_type: str | None = Field(None, description="e.g. desktop, mobile")
    referrer: str | None = Field(None, description="Referring URL")
    metadata_payload: dict[str, Any] | None = Field(default_factory=dict, description="Any additional context")

    model_config = ConfigDict(from_attributes=True)


class BehavioralBatchRequest(BaseModel):
    events: list[BehavioralEventPayload]
    anonymous_id: str | None = Field(None, description="Required if user is unauthenticated")


class ReadingSessionResponse(BaseModel):
    session_id: str
    article_id: int
    article_title: str | None = None
    article_slug: str | None = None
    started_at: datetime
    last_activity_at: datetime
    total_reading_seconds: int
    completion_percentage: int
    is_completed: bool

    model_config = ConfigDict(from_attributes=True)


class UserInterestResponse(BaseModel):
    entity_type: str
    entity_id: str
    affinity: float
    expertise: float
    confidence: float
    model_version: str
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)
