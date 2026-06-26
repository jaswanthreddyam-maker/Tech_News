import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.article import ProcessedArticle  # noqa
from app.models.base import Base
from app.models.user import User  # noqa


def utc_now():
    return datetime.now(timezone.utc)


class BehavioralEvent(Base):
    __tablename__ = "behavioral_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    anonymous_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("processed_articles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    content_version: Mapped[str] = mapped_column(String(50), nullable=True)

    scroll_percent: Mapped[int] = mapped_column(Integer, nullable=True)
    reading_time_seconds: Mapped[int] = mapped_column(Integer, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    device_type: Mapped[str] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="WEB", nullable=False)
    referrer: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_payload: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    # Relationships
    user = relationship("User")
    article = relationship("ProcessedArticle")

    __table_args__ = (
        Index("ix_behav_events_user_session", "user_id", "session_id"),
        Index("ix_behav_events_anon_session", "anonymous_id", "session_id"),
    )


class ReadingSession(Base):
    __tablename__ = "reading_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    anonymous_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("processed_articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_version: Mapped[str] = mapped_column(String(50), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    total_reading_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0)
    max_scroll_percent: Mapped[int] = mapped_column(Integer, default=0)

    device_type: Mapped[str] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(255), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Relationships
    user = relationship("User")
    article = relationship("ProcessedArticle")


class UserInterest(Base):
    __tablename__ = "user_interests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    anonymous_id: Mapped[str] = mapped_column(String(255), index=True, nullable=True)

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CATEGORY, TOPIC, TAG, COMPANY, PERSON
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)

    affinity: Mapped[float] = mapped_column(Float, default=0.0)
    expertise: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_user_interests_user_entity", "user_id", "entity_type", "entity_id", unique=True),
        Index("ix_user_interests_anon_entity", "anonymous_id", "entity_type", "entity_id", unique=True),
    )
