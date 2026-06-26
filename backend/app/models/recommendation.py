import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class AffinitySubjectType(str, enum.Enum):
    TOPIC = "TOPIC"
    ENTITY = "ENTITY"
    AUTHOR = "AUTHOR"
    ARTICLE = "ARTICLE"
    CATEGORY = "CATEGORY"
    TAG = "TAG"
    COMPANY = "COMPANY"
    PERSON = "PERSON"

class UserAffinityProfile(Base):
    """
    Generic tracker of user/session affinities for topics, entities, authors, etc.
    """
    __tablename__ = "user_affinity_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False) # Can be session_id if anonymous

    subject_type = Column(Enum(AffinitySubjectType), nullable=False)
    subject_id = Column(String(255), nullable=False)

    weight = Column(Float, default=0.0, nullable=False)
    source = Column(String(100), nullable=True) # e.g., 'implicit', 'explicit_follow'

    last_updated = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index('ix_user_affinity_user_subject', 'user_id', 'subject_type', 'subject_id', unique=True),
    )


class ArticleFeatureVector(Base):
    """
    Deterministic attributes of an article for query-time ranking.
    """
    __tablename__ = "article_feature_vectors"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String(255), nullable=False, unique=True)

    primary_topic = Column(String(255), nullable=True)
    entities = Column(JSONB, default=list, nullable=False)

    freshness_score = Column(Float, default=1.0, nullable=False) # Wait, user said replace freshness/popularity with the new ones, but maybe keep freshness as part of engagement? User said: "Instead of popularity_score, freshness_score, quality_score, I'd store behavior_score, editorial_score, knowledge_score, social_score, distribution_score, engagement_score"
    behavior_score = Column(Float, default=0.0, nullable=False)
    editorial_score = Column(Float, default=1.0, nullable=False)
    knowledge_score = Column(Float, default=1.0, nullable=False)
    social_score = Column(Float, default=0.0, nullable=False)
    distribution_score = Column(Float, default=0.0, nullable=False)
    engagement_score = Column(Float, default=0.0, nullable=False)

    @property
    def overall_score(self) -> float:
        return (self.behavior_score + self.editorial_score + self.knowledge_score + 
                self.social_score + self.distribution_score + self.engagement_score) # type: ignore

    language = Column(String(10), nullable=True)
    region = Column(String(50), nullable=True)
    reading_time = Column(Integer, default=0, nullable=False)

    embedding_version = Column(Integer, nullable=True)

    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class RecommendationProfile(Base):
    """
    Canonical read model for recommendation capabilities, abstracting raw feature vectors.
    """
    __tablename__ = "recommendation_profiles"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String(255), nullable=False, unique=True)
    profile_version = Column(String(50), default="1.0", nullable=False)
    feature_vector_id = Column(String(255), nullable=True)

    ranking_features = Column(JSONB, default=dict, nullable=False)
    context_features = Column(JSONB, default=dict, nullable=False)

    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Pre-calculated index for fast trending queries
    # Note: Actual SQL ranking often multiplies these at query time. We can create expression indexes if needed.
