import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from app.models.base import Base


class WorkspaceEntryStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class WorkspaceSnapshotModel(Base):
    """
    Git-like versioning for Workspace (ADR-0069).
    """
    __tablename__ = "workspace_snapshots"

    snapshot_id = Column(String(255), primary_key=True)
    goal_id = Column(String(255), nullable=False, index=True)
    parent_snapshot_id = Column(String(255), nullable=True)
    generation = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class WorkspaceBranch(Base):
    """
    Search tree branches for the Scheduler (ADR-0072).
    """
    __tablename__ = "workspace_branches"

    branch_id = Column(String(255), primary_key=True)
    goal_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    head_snapshot_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class WorkspaceEntry(Base):
    """
    Append-only Shared Workspace (Blackboard) entry (ADR-0065, ADR-0067).
    """
    __tablename__ = "workspace_entries"

    entry_id = Column(String(255), primary_key=True)
    goal_id = Column(String(255), nullable=False, index=True)
    branch_id = Column(String(255), nullable=False)
    section = Column(String(100), nullable=False) # e.g. "Research"
    producer_agent = Column(String(100), nullable=False)
    artifact_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default=WorkspaceEntryStatus.PENDING)
    version = Column(String(50), nullable=False)
    snapshot_id = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    dependencies = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class WorkspaceSnapshot:
    """
    In-memory representation of the workspace at a specific point in time,
    passed to agents for pure execution.
    """
    def __init__(self, snapshot_id: str, goal_id: str, entries: list):
        self.snapshot_id = snapshot_id
        self.goal_id = goal_id
        self.entries = entries
