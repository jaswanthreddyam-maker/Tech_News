from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EditorialDecisionLog(Base):
    __tablename__ = "tnt_editorial_decision_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    article_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    impact_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    freshness_multiplier: Mapped[float] = mapped_column(Numeric, nullable=False)
    effective_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    ranking_position: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    selection_reason_code: Mapped[str] = mapped_column(String(50), nullable=False)
    selection_reason_details: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
