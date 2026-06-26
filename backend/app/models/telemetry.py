from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base

class TimelineNodeType(str, Enum):
    EVENT = "EVENT"
    METRIC = "METRIC"
    HEALTH_CHECK = "HEALTH_CHECK"
    RECOVERY = "RECOVERY"
    ALERT = "ALERT"
    AI_DECISION = "AI_DECISION"

class RecoveryExecutionLog(Base):
    """Immutable ledger of all autonomous recovery executions."""
    __tablename__ = "recovery_execution_logs"
    
    id = Column(Integer, primary_key=True)
    recovery_id = Column(String, unique=True, index=True, nullable=False) # REC-YYYYMMDD-XXXX
    policy_name = Column(String, index=True, nullable=False)
    trigger_reason = Column(Text, nullable=False)
    mode = Column(String, nullable=False) # dry_run or active
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String, index=True, nullable=False)

class TimelineNode(Base):
    """Canonical vocabulary for the Root Cause Explorer, storing the causal chain of events."""
    __tablename__ = "timeline_nodes"
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String, index=True, nullable=False)
    node_type = Column(SQLEnum(TimelineNodeType, name="timeline_node_type"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    caused_by_id = Column(Integer, ForeignKey("timeline_nodes.id"), nullable=True)
    metadata_json = Column(JSONB, nullable=True) # stores evidence_sources and context

class RootCauseTimeline(Base):
    """Aggregates a complete causal chain into a resolvable incident for Sprint 5 AI."""
    __tablename__ = "root_cause_timelines"
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String, unique=True, index=True, nullable=False)
    root_event_id = Column(Integer, ForeignKey("timeline_nodes.id"), nullable=False)
    status = Column(String, nullable=False, default="unresolved") # unresolved, resolved, pending_human, auto_mitigated
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class RootCauseAnalysis(Base):
    """Deterministic output of the Rule Engine (Sprint 5.0), to be consumed by AI (Sprint 5.1)."""
    __tablename__ = "root_cause_analyses"
    
    id = Column(Integer, primary_key=True)
    correlation_id = Column(String, unique=True, index=True, nullable=False)
    timeline_id = Column(Integer, ForeignKey("root_cause_timelines.id"), nullable=True)
    root_cause = Column(String, nullable=False) # e.g. "CQRS Projection Lag"
    analysis_version = Column(String, nullable=False, default="v1-rule-engine")
    confidence_score = Column(Float, nullable=False) # Calculated 0.0 to 1.0
    confidence_factors = Column(JSONB, nullable=False) # e.g. [{"evidence": "...", "weight": 0.4}]
    status = Column(String, nullable=False) # OPEN, AUTO_RESOLVED, MANUAL_REQUIRED, CLOSED
    generated_by = Column(String, nullable=False) # RULE_ENGINE, AI_EXPLORER, HUMAN
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    explanation = relationship("RootCauseExplanation", back_populates="analysis", uselist=False)

class RootCauseExplanation(Base):
    """AI Explanation Layer (Sprint 5.1). Explicitly isolated from deterministic truth."""
    __tablename__ = "root_cause_explanations"
    
    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey("root_cause_analyses.id", ondelete="CASCADE"), unique=True, nullable=False)
    explanation = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    generated_by = Column(String, nullable=False) # e.g. "LLMExplanationProvider"
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    analysis = relationship("RootCauseAnalysis", back_populates="explanation")
