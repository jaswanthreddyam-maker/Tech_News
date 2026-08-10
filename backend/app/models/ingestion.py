from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class IngestionCycleMetrics(Base):
    __tablename__ = "ingestion_cycle_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    sources_scanned: Mapped[int] = mapped_column(Integer, default=0)
    sources_crawled: Mapped[int] = mapped_column(Integer, default=0)
    articles_discovered: Mapped[int] = mapped_column(Integer, default=0)
    articles_saved: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0)
    filtered_skipped: Mapped[int] = mapped_column(Integer, default=0)
    failed_crawls: Mapped[int] = mapped_column(Integer, default=0)
    
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="started")
