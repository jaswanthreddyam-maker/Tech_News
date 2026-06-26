from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArticlePublishedPayload(BaseModel):
    """
    CQRS Contract for the ArticlePublished event.
    This guarantees that the Read Model receives all necessary fields from the Write Model
    (including all scores) so that the HomepageBuilder has accurate ranking data.
    """
    id: str
    url: str
    title: str
    content: str
    summary: str | None = None
    hash: str
    source: str
    thumbnail_url: str | None = None
    thumbnail_local: str | None = None
    thumbnail_type: str | None = "REAL_IMAGE"
    published_at: datetime | None = None
    is_test_data: bool = False
    key_takeaways: list[dict[str, Any]] | None = None
    
    # Critical Scoring Fields
    impact_score: float = 0.0
    freshness_score: float = 0.0
    engagement_score: float = 0.0
    final_score: float = 0.0
    
    # Metadata Fields
    reading_time: int = 0
    tags: str | None = None
    category: str | None = None
    published_status: str | None = None

    model_config = ConfigDict(extra="ignore")


class ArticleThumbnailUpdatedPayload(BaseModel):
    id: str
    thumbnail_url: str | None = None
    thumbnail_local: str | None = None
    thumbnail_type: str | None = "REAL_IMAGE"


class AIThumbnailGenerationRequested(BaseModel):
    article_id: int
    reason: str
    requested_at: datetime


class AIThumbnailGenerated(BaseModel):
    article_id: int
    thumbnail_url: str
    thumbnail_local: str
    generation_duration_ms: int
    model_used: str
    generated_at: datetime


class AIThumbnailGenerationFailed(BaseModel):
    article_id: int
    error: str
    failed_at: datetime


class AIThumbnailRejected(BaseModel):
    article_id: int
    confidence: float
    reason: str
    rejected_at: datetime
