"""
Projection Models — Enterprise CQRS Read Projections.
Contains versioned, immutable read model projections for Instant API Serving.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, DateTime, Integer, JSON
from app.models.base import Base


class HomepageProjection(Base):
    """
    Immutable versioned homepage read model projection.
    Stores pre-aggregated top 10 RankedStory[] payload and editorial decision logs.
    """
    __tablename__ = "homepage_projections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    projection_version = Column(Integer, nullable=False, index=True)
    ranking_version = Column(String(32), nullable=False, default="2.1")
    pipeline_version = Column(String(32), nullable=False, default="1.0.0")
    generated_by = Column(String(64), nullable=False, default="HomepageBuilder")
    stories_json = Column(JSON, nullable=False)
    explanation_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class CategoryDeskProjection(Base):
    """
    Immutable versioned Category Desk read model projection.
    Stores pre-computed arrays of article IDs per category desk.
    """
    __tablename__ = "category_desk_projections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_slug = Column(String(64), nullable=False, index=True)
    article_count = Column(Integer, nullable=False, default=0)
    article_ids = Column(JSON, nullable=False)
    projection_version = Column(String(32), nullable=False, default="1.0.0")
    algorithm_version = Column(String(32), nullable=False, default="1.0.0")
    policy_version = Column(String(32), nullable=False, default="1.0.0")
    build_duration_ms = Column(Integer, nullable=False, default=0)
    rebuilt_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
