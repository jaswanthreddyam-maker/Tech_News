from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from app.models.base import Base


class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(1000), nullable=False)
    intent = Column(String(100), nullable=False)
    execution_plan = Column(JSON, nullable=False)
    snapshot_id = Column(Integer, nullable=False)
    # Status transitions: CREATED -> PLANNED -> EXECUTING -> RETRIEVED -> GENERATING -> VALIDATING -> COMPLETED / FAILED
    status = Column(String(50), default="CREATED") 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ExecutionAttempt(Base):
    __tablename__ = "execution_attempts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    planner_version = Column(String(50), nullable=False)
    workflow_hash = Column(String(255), nullable=False)
    snapshot_id = Column(Integer, nullable=False)
    optimizer_version = Column(String(50), nullable=False)
    provider_versions = Column(JSON, nullable=False)
    failure_reason = Column(String(1000), nullable=True)
    resume_from = Column(String(255), nullable=True)

class EvidenceTree(Base):
    __tablename__ = "evidence_trees"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False)
    claim = Column(String(1000), nullable=False)
    evidence_payload = Column(JSON, nullable=False) # Maps Artifact -> Observation -> Node -> Citation
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ResearchArtifact(Base):
    __tablename__ = "research_artifacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False)
    # Inherits or references BaseAIArtifact concepts via payload
    payload = Column(JSON, nullable=False)
    confidence_breakdown = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
