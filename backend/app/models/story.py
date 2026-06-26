from datetime import datetime, timezone
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Float, ForeignKey, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List

from app.models.base import Base

class StoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    MONITORING = "MONITORING"
    DORMANT = "DORMANT"
    ARCHIVED = "ARCHIVED"

class StoryMilestoneType(str, Enum):
    INITIAL_BREAK = "INITIAL_BREAK"
    MAJOR_UPDATE = "MAJOR_UPDATE"
    OFFICIAL_RESPONSE = "OFFICIAL_RESPONSE"
    MARKET_REACTION = "MARKET_REACTION"
    FOLLOW_UP = "FOLLOW_UP"
    ANALYSIS = "ANALYSIS"

class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[StoryStatus] = mapped_column(SQLEnum(StoryStatus), default=StoryStatus.ACTIVE)
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Optional reference to the foundational breaking article that spawned this story
    primary_article_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("articles.id"), nullable=True)
    
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True) # ID or Email of editor/system
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # 1 -> N relationship back to Articles
    articles = relationship("ProcessedArticle", back_populates="story", foreign_keys="ProcessedArticle.story_id")

class StoryTimelineEvent(Base):
    __tablename__ = "story_timeline_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    story_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    source_event_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., StoryCreated, ArticleAssignedToStory, StoriesMerged, StoryReawakened
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    # Context
    article_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    milestone_type: Mapped[Optional[StoryMilestoneType]] = mapped_column(SQLEnum(StoryMilestoneType), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

class StoryAssignmentDecision(Base):
    """Audit log for automated duplicate detection / story assignment decisions."""
    __tablename__ = "story_assignment_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    article_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    candidate_story_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_used: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False) # AUTO_ASSIGN, EDITOR_REVIEW, NEW_STORY
    decision_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class StoryDashboardProjection(Base):
    __tablename__ = "story_dashboard_projections"
    
    story_id = Column(String(255), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    editorial_status = Column(String(50), nullable=False, default='DRAFT')
    publication_status = Column(String(50), nullable=False, default='DRAFT')
    
    unique_readers = Column(Integer, default=0, nullable=False)
    views = Column(Integer, default=0, nullable=False)
    bookmarks = Column(Integer, default=0, nullable=False)
    newsletter_clicks = Column(Integer, default=0, nullable=False)
    article_count = Column(Integer, default=0, nullable=False)
    
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    projection_version = Column(Integer, default=1, nullable=False)

class StoryHealthProjection(Base):
    """
    Derived Projection representing the real-time health and momentum of a story.
    UPDATED ONLY BY: StoryHealthAggregationTask (e.g. every 15 minutes).
    Timeline events and StoryProjector MUST NOT mutate this table directly.
    """
    __tablename__ = "story_health_projections"
    
    story_id = Column(String(255), primary_key=True)
    
    # Structural State (From Projector)
    story_status = Column(String(50), default="ACTIVE")
    days_since_activity = Column(Integer, default=0)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    
    # Telemetry State (From TelemetryAggregator)
    momentum = Column(Float, default=0.0)
    trend = Column(String(50), default="FLAT") # UPWARD, FLAT, DECAYING
    coverage_score = Column(Float, default=0.0)
    attention_score = Column(Float, default=0.0) # Copilot metric
    reawakening_signal_score = Column(Float, default=0.0) # 0-100 explainable score
    projection_version = Column(Integer, default=1, nullable=False)

from enum import Enum as PyEnum

class StoryRelationshipType(str, PyEnum):
    SIMILAR_TO = "SIMILAR_TO"
    MENTIONS = "MENTIONS"
    EVOLVES_FROM = "EVOLVES_FROM"
    FOLLOW_UP = "FOLLOW_UP"

class RelatedStory(Base):
    """Network graph of related stories, used for the 'Related Coverage' feature."""
    __tablename__ = "related_stories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_story_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    target_story_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    relationship_type: Mapped[StoryRelationshipType] = mapped_column(String(50), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint('source_story_id', 'target_story_id', name='uq_related_story_pair'),
    )
