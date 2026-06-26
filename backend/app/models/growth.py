from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import utc_now


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    default_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    environment_states: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    rules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class RuntimeConfiguration(Base):
    __tablename__ = "runtime_configurations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    default_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    environment_states: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    rules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT") # DRAFT, SCHEDULED, RUNNING, PAUSED, COMPLETED, ARCHIVED
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False, default="USER") # USER, SESSION, DEVICE
    assignment_strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="HASH") # HASH, RANDOM, MANUAL

    allocation_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    mutual_exclusion_group_id: Mapped[str] = mapped_column(String(255), nullable=True)

    environment_states: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    rules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    primary_goal: Mapped[str] = mapped_column(String(255), nullable=True)
    secondary_goals: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    variants = relationship("ExperimentVariant", back_populates="experiment", cascade="all, delete-orphan")

class ExperimentVariant(Base):
    __tablename__ = "experiment_variants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    experiment = relationship("Experiment", back_populates="variants")

class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("experiment_variants.id"), nullable=False)

    subject_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)

    assignment_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    assignment_version: Mapped[str] = mapped_column(String(50), nullable=False)

    assigned_by: Mapped[str] = mapped_column(String(50), nullable=False, default="HASH")
    assignment_reason: Mapped[str] = mapped_column(String(255), nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    exposure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_exposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class ExperimentMetrics(Base):
    """
    Projected Read Model for Experiment Analytics
    """
    __tablename__ = "experiment_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("experiment_variants.id"), nullable=False)

    time_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    total_assigned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_exposed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_converted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lift: Mapped[float] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class Funnel(Base):
    __tablename__ = "funnels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT") # DRAFT, SCHEDULED, ACTIVE, PAUSED, ARCHIVED
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False, default="USER")
    time_window_seconds: Mapped[int] = mapped_column(Integer, nullable=True) # Optional expiration

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    steps = relationship("FunnelStep", back_populates="funnel", cascade="all, delete-orphan")

class FunnelStep(Base):
    __tablename__ = "funnel_steps"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    funnel_id: Mapped[int] = mapped_column(ForeignKey("funnels.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Example format: {"type": "ARTICLE_VIEWED", "conditions": {"is_unique": True}, "version": "v1"}
    event_matcher: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    funnel = relationship("Funnel", back_populates="steps")

class FunnelState(Base):
    """
    Operational record of a subject's progression through a funnel.
    """
    __tablename__ = "funnel_states"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    funnel_id: Mapped[int] = mapped_column(ForeignKey("funnels.id"), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    state_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")

    # Snapshot of {country, language, experiment, feature_flags, device, source, campaign}
    dimension_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    current_step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    entered_step_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

class FunnelMetrics(Base):
    """
    Projected read model for funnel analytics.
    """
    __tablename__ = "funnel_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    funnel_id: Mapped[int] = mapped_column(ForeignKey("funnels.id"), nullable=False)

    time_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    dimension_key: Mapped[str] = mapped_column(String(255), nullable=False, default="ALL")

    total_started: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Store counts keyed by step order, e.g. {"1": 100, "2": 80, "3": 50}
    step_counts: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    conversion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dropoff_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    average_completion_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    median_completion_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT") # DRAFT, ACTIVE, ARCHIVED
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False, default="USER")
    refresh_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="REAL_TIME") # REAL_TIME, SCHEDULED, MANUAL

    parent_cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    rules = relationship("CohortRule", back_populates="cohort", cascade="all, delete-orphan")
    parent_cohort = relationship("Cohort", remote_side=[id], backref="child_cohorts")

class CohortRule(Base):
    __tablename__ = "cohort_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id"), nullable=False)
    rule_capability: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. EventCountRule, PropertyRule, FunnelRule

    # Boolean expression or parameters config
    expression: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    cohort = relationship("Cohort", back_populates="rules")

class CohortMembership(Base):
    __tablename__ = "cohort_memberships"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id"), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ENTERED") # ENTERED, EXITED, PAUSED
    reason: Mapped[str] = mapped_column(String(255), nullable=True)

    cohort_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    rule_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    projection_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    removed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

class CohortSnapshot(Base):
    __tablename__ = "cohort_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id"), nullable=False, index=True)

    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    growth_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
