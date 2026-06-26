import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class CertificationRun(Base):
    __tablename__ = "certification_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[str] = mapped_column(String, index=True, nullable=False, unique=True)
    certification_type: Mapped[str] = mapped_column(String, nullable=False) # NIGHTLY, WEEKLY, MANUAL, PRE_RELEASE
    certification_runner_version: Mapped[str] = mapped_column(String, nullable=False)
    baseline_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_scenarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grade: Mapped[str] = mapped_column(String, nullable=False) # A+, A, B, C, F
    
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    evidences: Mapped[List["CertificationScenarioEvidence"]] = relationship(
        "CertificationScenarioEvidence",
        back_populates="run",
        cascade="all, delete-orphan"
    )

class CertificationScenarioEvidence(Base):
    __tablename__ = "certification_scenario_evidences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("certification_runs.id"), nullable=False, index=True)
    
    scenario_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    
    detection_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recovery_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    root_cause_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    explanation_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    event_loss: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    projection_consistent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    chain_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sla_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    run: Mapped["CertificationRun"] = relationship("CertificationRun", back_populates="evidences")
