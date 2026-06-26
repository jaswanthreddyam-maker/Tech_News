from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ProjectionCheckpoint(Base):
    """
    Ensures exactly-once processing and replayability across the entire platform.
    """
    __tablename__ = "projection_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    projection_group = Column(String(100), nullable=False) # e.g., 'analytics', 'knowledge', 'distribution'
    projector_name = Column(String(100), nullable=False)
    projector_version = Column(Integer, nullable=False)
    event_id = Column(Integer, ForeignKey("event_envelopes.id", ondelete="CASCADE"), nullable=False)

    processed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    checksum = Column(String(255), nullable=True)

    __table_args__ = (
        Index('ix_proj_chkpt_group_proj_event', 'projection_group', 'projector_name', 'event_id', unique=True),
    )


class ProjectionFailure(Base):
    """
    Captures projection errors for Operations Console auto-retry and auditing.
    """
    __tablename__ = "projection_failures"

    id = Column(Integer, primary_key=True, index=True)
    projection_group = Column(String(100), nullable=False)
    projector_name = Column(String(100), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("event_envelopes.id", ondelete="CASCADE"), nullable=False, index=True)

    error = Column(Text, nullable=False)
    stacktrace = Column(Text, nullable=True)

    # Retry Scheduling
    attempt_count = Column(Integer, default=1, nullable=False)
    retry_after = Column(DateTime(timezone=True), nullable=True)
    next_attempt = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    resolved = Column(Integer, default=0, nullable=False) # 0=False, 1=True
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class ProjectionTelemetry(Base):
    """
    Health metrics for individual projectors, useful for Operations Console.
    """
    __tablename__ = "projection_telemetry"

    id = Column(Integer, primary_key=True, index=True)
    projection_group = Column(String(100), nullable=False)
    projector_name = Column(String(100), nullable=False, unique=True)

    events_processed = Column(Integer, default=0, nullable=False)
    queue_depth = Column(Integer, default=0, nullable=False)

    avg_latency_ms = Column(Float, default=0.0, nullable=False)
    max_latency_ms = Column(Float, default=0.0, nullable=False)
    replay_duration_ms = Column(Float, default=0.0, nullable=False)

    failure_rate = Column(Float, default=0.0, nullable=False)

    last_processed_event_id = Column(Integer, nullable=True)
    last_success = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
