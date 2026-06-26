from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String

from app.models.base import Base


class EventOutbox(Base):
    __tablename__ = "event_outbox"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)

    # State machine: CREATED -> LEASED -> DISPATCHING -> DELIVERED -> FAILED -> RETRYING -> DEAD_LETTER -> ARCHIVED
    status = Column(String(50), default="CREATED", nullable=False)

    lease_id = Column(String(100), nullable=True) # UUID of the worker claiming the lease
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class DeadLetterEvent(Base):
    __tablename__ = "dead_letter_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_outbox_id = Column(Integer, nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    failure_reason = Column(String(2000), nullable=False)
    failed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
