from datetime import datetime, timezone
from typing import Any
import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.models.base import Base
from app.models.source import Source
import app.models.story


class EditorialStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PublicationStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ThumbnailFailureReason(str, enum.Enum):
    NO_IMAGES_FOUND = "NO_IMAGES_FOUND"
    HOTLINK_PROTECTION = "HOTLINK_PROTECTION"
    BOT_BLOCKED = "BOT_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_DENIED = "ACCESS_DENIED"
    SOURCE_RESTRICTED = "SOURCE_RESTRICTED"
    DOWNLOAD_TIMEOUT = "DOWNLOAD_TIMEOUT"
    WORKER_FAILURE = "WORKER_FAILURE"
    QUEUE_FAILURE = "QUEUE_FAILURE"
    PROJECTION_FAILURE = "PROJECTION_FAILURE"
    PIPELINE_FAILURE = "PIPELINE_FAILURE"
    UNKNOWN = "UNKNOWN"


class RawArticle(Base):
    __tablename__ = "raw_articles"
    __table_args__ = (
        UniqueConstraint("url_hash", "title_hash", name="uq_url_title_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), unique=False, nullable=False, index=True)
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    compressed_html: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    clean_text: Mapped[str] = mapped_column(Text, nullable=True)
    article_metadata: Mapped[str] = mapped_column(Text, nullable=True)
    parser_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(String(50), default="discovered", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    error_log: Mapped[str] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    html_refetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    dead_letter_reason: Mapped[str] = mapped_column(Text, nullable=True)
    dead_letter_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_test_data: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')

    # Relationships
    source = relationship("Source", back_populates="raw_articles")
    processed_articles = relationship("ProcessedArticle", back_populates="raw_article", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    processed_articles = relationship("ProcessedArticle", back_populates="category")


class ProcessedArticle(Base):
    __tablename__ = "processed_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    story_id: Mapped[str | None] = mapped_column(String, ForeignKey("stories.id", ondelete="SET NULL"), nullable=True)
    raw_article_id: Mapped[int] = mapped_column(Integer, ForeignKey("raw_articles.id", ondelete="SET NULL"), nullable=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_takeaways: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String(150), nullable=False)
    hero_image: Mapped[str] = mapped_column(String, nullable=True)
    source_name: Mapped[str] = mapped_column(String(150), default="System")
    source_url: Mapped[str] = mapped_column(String, nullable=True)
    clean_html: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=True)
    ai_confidence: Mapped[float] = mapped_column(Numeric, default=95.0)
    reading_time: Mapped[int] = mapped_column(Integer, default=3)
    editorial_status: Mapped[EditorialStatus] = mapped_column(String(50), default=EditorialStatus.DRAFT, index=True)
    publication_status: Mapped[PublicationStatus | None] = mapped_column(String(50), nullable=True, index=True)
    published_status: Mapped[str] = mapped_column(String(50), default="draft", index=True) # Deprecated
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    seo_title: Mapped[str] = mapped_column(String(255), nullable=True)
    seo_keywords: Mapped[str] = mapped_column(Text, nullable=True)
    readability_score: Mapped[int] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    hero_image: Mapped[str] = mapped_column(String, nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(Text, nullable=True)
    thumbnail_local: Mapped[str] = mapped_column(Text, nullable=True)
    thumbnail_status: Mapped[str] = mapped_column(String(50), default="pending")
    thumbnail_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    thumbnail_source: Mapped[str] = mapped_column(String(50), nullable=True)
    thumbnail_quality_score: Mapped[int] = mapped_column(Integer, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    winner_pass: Mapped[str] = mapped_column(String, nullable=True)
    selected_score: Mapped[int] = mapped_column(Integer, nullable=True)
    thumbnail_score: Mapped[int] = mapped_column(Integer, nullable=True)
    thumbnail_algorithm_version: Mapped[str] = mapped_column(String(50), nullable=True)
    thumbnail_type: Mapped[str] = mapped_column(String(50), default="REAL_IMAGE", server_default="REAL_IMAGE")
    thumbnail_generation_reason: Mapped[str] = mapped_column(String(100), nullable=True)
    thumbnail_generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_by: Mapped[str] = mapped_column(String(150), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False) # Deprecated, use publication_status
    freshness_score: Mapped[float] = mapped_column(Numeric, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Numeric, default=0.0)
    final_score: Mapped[float] = mapped_column(Numeric, default=0.0)
    is_test_data: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    editorial_version: Mapped[str] = mapped_column(String(50), nullable=True)
    enrichment_status: Mapped[str] = mapped_column(String(50), default="pending", server_default="pending")
    completed_enrichment_stages: Mapped[list] = mapped_column(JSON, default=list, server_default='[]')


    embedding_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    embedding = mapped_column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    embedding_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    cluster_id: Mapped[str] = mapped_column(String(36), index=True, nullable=True)
    cluster_score: Mapped[float] = mapped_column(Numeric, nullable=True)
    cluster_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    cluster_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    raw_article = relationship("RawArticle", back_populates="processed_articles")
    source_ref = relationship("Source", back_populates="processed_articles") # link source_id back to Source
    category = relationship("Category", back_populates="processed_articles")
    story = relationship("app.models.story.Story", back_populates="articles", foreign_keys=[story_id])

    __table_args__ = (
        Index('ix_processed_articles_embedding', 'embedding', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )


class AIThumbnailMetadata(Base):
    __tablename__ = "ai_thumbnail_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("processed_articles.id", ondelete="CASCADE"), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    entities_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    prompt_used: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    generation_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ArticleReadModel(Base):
    """Disposable SQL read model projected from ArticleArtifacts."""
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)  # Links to ArticleArtifact ID
    story_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    url: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    canonical_url: Mapped[str] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(150), nullable=True)
    
    editorial_status: Mapped[str] = mapped_column(String(50), default="DRAFT", index=True)
    publication_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_by: Mapped[str] = mapped_column(String(150), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    reading_time: Mapped[int] = mapped_column(Integer, default=0)
    images: Mapped[dict] = mapped_column(JSON, default=list)
    tags: Mapped[dict] = mapped_column(JSON, default=list)
    key_takeaways: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(150), nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String, nullable=True)
    thumbnail_local: Mapped[str] = mapped_column(String, nullable=True)
    thumbnail_type: Mapped[str] = mapped_column(String(50), default="REAL_IMAGE", server_default="REAL_IMAGE")
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    freshness_score: Mapped[float] = mapped_column(Numeric, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Numeric, default=0.0)
    final_score: Mapped[float] = mapped_column(Numeric, default=0.0)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    published_status: Mapped[str] = mapped_column(String(50), nullable=True)
    is_test_data: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')

    embedding = mapped_column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    embedding_version: Mapped[str] = mapped_column(String(50), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index(
            "ix_article_read_model_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
