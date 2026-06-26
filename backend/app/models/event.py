import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class EventCategory(enum.Enum):
    DISTRIBUTION = "DISTRIBUTION"
    EDITORIAL = "EDITORIAL"
    KNOWLEDGE = "KNOWLEDGE"
    ANALYTICS = "ANALYTICS"
    AUTH = "AUTH"
    SYSTEM = "SYSTEM"
    BEHAVIORAL = "BEHAVIORAL"
    AGENT = "AGENT"

class EventSubjectType(enum.Enum):
    ARTICLE = "ARTICLE"
    NEWSLETTER = "NEWSLETTER"
    DISTRIBUTION_JOB = "DISTRIBUTION_JOB"
    PUBLICATION = "PUBLICATION"
    COMMENT = "COMMENT"
    ENTITY = "ENTITY"
    TOPIC = "TOPIC"
    USER = "USER"
    WORKSPACE = "WORKSPACE"
    AGENT_SESSION = "AGENT_SESSION"
    AGENT_EXECUTION = "AGENT_EXECUTION"

class EventEnvelope(Base):
    __tablename__ = "event_envelopes"

    id = Column(Integer, primary_key=True, index=True)

    # Event Classification
    category = Column(Enum(EventCategory), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True) # e.g. EMAIL_OPENED, ARTICLE_PUBLISHED

    # Subject identity
    subject_type = Column(Enum(EventSubjectType), nullable=False, index=True)
    subject_id = Column(String(255), nullable=False, index=True)

    # Source / Provider Identity
    provider = Column(String(100), nullable=False, index=True) # e.g. SENDGRID, APPLE_NEWS, INTERNAL
    provider_event_id = Column(String(255), nullable=True, index=True)

    # Correlation (Traceability)
    correlation_id = Column(String(255), nullable=True, index=True)
    trace_id = Column(String(255), nullable=True, index=True)
    causation_id = Column(String(255), nullable=True, index=True)

    # Timing
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Data payloads
    payload = Column(JSONB, nullable=False, default=dict)
    event_metadata = Column(JSONB, nullable=True)

    # Schema versioning
    schema_version = Column(String(50), nullable=False, default="1.0")
    event_version = Column(String(50), nullable=False, default="1.0")
