from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class FeedEntry(BaseModel):
    """Output of RSSIngestionCapability"""
    feed_url: HttpUrl
    entry_url: HttpUrl
    title: str
    published_at: datetime | None
    author: str | None

class RawDocument(BaseModel):
    """Output of WebFetchCapability"""
    url: HttpUrl
    status_code: int
    headers: dict[str, str]
    raw_html: str
    fetch_time_ms: int
    redirected_url: HttpUrl | None

class SourceAssessment(BaseModel):
    """Output of SourceValidationCapability"""
    url: HttpUrl
    is_reachable: bool
    is_https: bool
    is_valid_html: bool
    is_fresh: bool
    technical_score: float  # 0.0 to 1.0

    trust_score: float      # 0.0 to 1.0
    is_spam: bool
    domain_reputation: str  # e.g., "HIGH", "UNKNOWN", "LOW"
    known_publisher: bool
    editorial_score: float  # 0.0 to 1.0

    is_approved: bool

class DuplicateDecision(BaseModel):
    """Output of DeduplicationCapability"""
    normalized_url: HttpUrl
    content_hash: str
    is_duplicate: bool
    matched_artifact_id: str | None
    confidence: float

class CanonicalArticle(BaseModel):
    """Output of ContentExtractionCapability. Rich definition per User guidelines."""
    id: str = Field(..., description="Unique ID for this article representation")
    url: HttpUrl
    canonical_url: HttpUrl | None
    title: str
    subtitle: str | None
    author: str | None
    published_at: datetime | None
    updated_at: datetime | None
    language: str = "en"
    summary: str | None
    content: str
    word_count: int
    reading_time: int
    images: list[str] = []
    tags: list[str] = []
    source: str
    license: str | None
    hash: str
