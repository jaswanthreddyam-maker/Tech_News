import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class DistributionJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    PREFLIGHT = "PREFLIGHT"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"

class DeliveryOutcome(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    DELIVERED = "DELIVERED"
    DEFERRED = "DEFERRED"
    HARD_BOUNCE = "HARD_BOUNCE"
    SOFT_BOUNCE = "SOFT_BOUNCE"

class EngagementEvent(str, enum.Enum):
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    UNSUBSCRIBED = "UNSUBSCRIBED"
    COMPLAINT = "COMPLAINT"

class SubjectType(str, enum.Enum):
    ARTICLE = "ARTICLE"
    NEWSLETTER = "NEWSLETTER"
    DIGEST = "DIGEST"
    NOTIFICATION = "NOTIFICATION"
    INVITATION = "INVITATION"

class DistributionManifest(Base):
    __tablename__ = "distribution_manifests"

    id = Column(Integer, primary_key=True, index=True)
    publication_record_id = Column(Integer, ForeignKey("publication_records.id"), nullable=False)

    subject_type = Column(String(50), nullable=False)
    channels = Column(JSONB, nullable=False, default=list)
    audience = Column(JSONB, nullable=True)
    distribution_version = Column(String(50), nullable=False, default="1.0")
    payload_version = Column(String(50), nullable=False, default="1.0")
    content_checksum = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    jobs = relationship("DistributionJob", back_populates="manifest", cascade="all, delete-orphan")
    publication_record = relationship("PublicationRecord", back_populates="distribution_manifest")

class DistributionJob(Base):
    __tablename__ = "distribution_jobs"

    id = Column(Integer, primary_key=True, index=True)
    manifest_id = Column(Integer, ForeignKey("distribution_manifests.id"), nullable=False)

    subject_type = Column(String, nullable=False, index=True)  # e.g., ARTICLE, NEWSLETTER
    subject_id = Column(String, nullable=False, index=True)    # e.g., artifact_id or hash

    channel = Column(String, nullable=False, index=True)       # e.g., RSS, SITEMAP, PUSH
    status = Column(Enum(DistributionJobStatus), default=DistributionJobStatus.QUEUED, nullable=False)

    payload = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    manifest = relationship("DistributionManifest", back_populates="jobs")
    reports = relationship("DeliveryReport", back_populates="job", cascade="all, delete-orphan")
class DeliveryReport(Base):
    __tablename__ = "delivery_reports"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("distribution_jobs.id"), nullable=False)

    status = Column(Enum(DistributionJobStatus), nullable=False)
    attempt = Column(Integer, default=1, nullable=False)
    duration_ms = Column(Integer, nullable=True)
    error = Column(String, nullable=True)
    provider_response = Column(JSONB, nullable=True)
    metadata_info = Column(JSONB, default=dict)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    job = relationship("DistributionJob", back_populates="reports")




