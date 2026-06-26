from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String

from app.models.base import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), nullable=False, unique=True)
    user_id = Column(Integer, nullable=True, index=True)

    # State machine: CREATED -> ACTIVE -> PLANNING -> EXECUTING -> RESPONDING -> WAITING -> COMPLETED / ARCHIVED
    status = Column(String(50), default="CREATED", nullable=False)

    active_research_session_id = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
