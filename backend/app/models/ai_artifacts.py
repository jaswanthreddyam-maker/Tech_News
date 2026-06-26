from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String

from app.models.base import Base


class AIArtifact(Base):
    __tablename__ = "ai_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    artifact_type = Column(String(50), nullable=False, index=True) # e.g. "SUMMARY", "TIMELINE"
    status = Column(String(50), nullable=False) # e.g. "CREATED", "VALIDATED", "ACTIVE", "SUPERSEDED", "ARCHIVED"
    version = Column(String(50), nullable=False)

    # Payload and Metadata
    payload = Column(JSON, nullable=False) # The actual content (StructuredSummary, etc.)
    metadata_json = Column(JSON, nullable=False) # provenance, validation, confidence

    article_id = Column(Integer, ForeignKey("processed_articles.id", ondelete="CASCADE"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True) # UUID for canonical merging

    # Timing
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    precision = Column(String(20), nullable=False) # "YEAR", "MONTH", "DAY", "HOUR", "UNKNOWN"

    # Details
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=False)
    importance = Column(Float, default=0.5)
    confidence = Column(Float, default=0.5)

    # Evidence & Relationships
    citations = Column(JSON, default=list) # List of sources/URLs
    entities = Column(JSON, default=list) # List of entities involved

    # An event might belong to an artifact or just stand alone linked via join table.
    # For now, linking to the primary AI artifact that generated it.
    artifact_id = Column(Integer, ForeignKey("ai_artifacts.id", ondelete="CASCADE"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
