from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.models.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventOutbox(Base):
    """
    Transactional outbox for reliable event dispatch.

    State machine (frozen contract):
        CREATED ──→ LEASED ──→ DISPATCHING ──→ DELIVERED (terminal)
                      │              │
                      │   (handler failure)
                      │              ↓
                      │           RETRYING ──→ LEASED (next poll)
                      │              │
                      │   (retry_count >= max_retries)
                      │              ↓
                      │         DEAD_LETTER (terminal)
                      │
                 (lease expired)
                      ↓
                   RETRYING

    Terminal states (DELIVERED, DEAD_LETTER) are immutable unless
    explicitly replayed by admin (which resets to CREATED).
    """
    __tablename__ = "event_outbox"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False)

    status = Column(String(50), default="CREATED", nullable=False, index=True)

    # Lease-based claiming for concurrent worker safety
    lease_id = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Retry tracking
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_log = Column(Text, nullable=True)

    # Traceability
    correlation_id = Column(String(255), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=_utc_now)
    updated_at = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


class OutboxDispatchCheckpoint(Base):
    """
    Handler-level idempotency for outbox event dispatch.

    Each handler that processes an outbox event records a checkpoint.
    Before invoking a handler, the dispatcher checks for an existing
    checkpoint and skips if found. This guarantees at-most-once execution
    per (handler_name, outbox_event_id) even under crash/retry scenarios.

    Separate from projection_checkpoints (which operate on EventEnvelope.id).
    """
    __tablename__ = "outbox_dispatch_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    handler_name = Column(String(100), nullable=False)
    outbox_event_id = Column(Integer, ForeignKey("event_outbox.id", ondelete="CASCADE"), nullable=False)
    processed_at = Column(DateTime(timezone=True), default=_utc_now)

    __table_args__ = (
        UniqueConstraint("handler_name", "outbox_event_id", name="uq_dispatch_chkpt"),
        Index("ix_dispatch_chkpt_lookup", "handler_name", "outbox_event_id"),
    )


class DeadLetterEvent(Base):
    __tablename__ = "dead_letter_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_outbox_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    failure_reason = Column(String(2000), nullable=False)
    failed_at = Column(DateTime(timezone=True), default=_utc_now)
