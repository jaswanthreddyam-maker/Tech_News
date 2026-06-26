from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    credibility_score: Mapped[int] = mapped_column(Integer, default=50)
    crawl_interval: Mapped[int] = mapped_column(Integer, default=3600)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    health_state: Mapped[str] = mapped_column(String(50), default="healthy")
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_crawl_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    parser_config: Mapped[str] = mapped_column(String, nullable=True)
    total_crawls: Mapped[int] = mapped_column(Integer, default=0)
    successful_crawls: Mapped[int] = mapped_column(Integer, default=0)
    reliability_score: Mapped[float] = mapped_column(Numeric, default=100.0)
    last_failure_type: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Relationships
    raw_articles = relationship("RawArticle", back_populates="source", cascade="all, delete-orphan")
    processed_articles = relationship("ProcessedArticle", back_populates="source_ref")
