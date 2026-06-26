from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class UserPrivacySettings(Base):
    __tablename__ = "user_privacy_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    history_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    personalization_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    behavioral_consent_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationship to user
    user = relationship("User")
