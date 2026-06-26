import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String

from app.models.base import Base


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_type = Column(String(50), nullable=False, index=True) # "ENTITY", "WORLD_EVENT", "CONCEPT", "TOPIC", "LOCATION"

    # Optional canonical name (e.g., "Microsoft")
    name = Column(String(255), index=True, nullable=True)

    # Generic properties (JSON) to store anything related to the node type
    properties = Column(JSON, default=dict)

    confidence = Column(Float, default=1.0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    source_node_id = Column(String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

    edge_type = Column(String(50), nullable=False, index=True) # "WORKS_FOR", "LOCATED_IN", "ACQUIRED", "ANNOUNCED", "PART_OF"

    properties = Column(JSON, default=dict)
    confidence = Column(Float, default=1.0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ArtifactReference(Base):
    __tablename__ = "artifact_references"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # The AIArtifact that references this graph component
    artifact_id = Column(Integer, ForeignKey("ai_artifacts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Target graph component
    graph_node_id = Column(String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    graph_edge_id = Column(String(36), ForeignKey("graph_edges.id", ondelete="CASCADE"), nullable=True, index=True)

    reference_type = Column(String(50), nullable=False) # "EXTRACTED", "SUPPORTING_EVIDENCE", "MENTIONED"

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class GraphNodeAlias(Base):
    __tablename__ = "graph_node_aliases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_node_id = Column(String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    alias = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class GraphVersion(Base):
    __tablename__ = "graph_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    version_number = Column(Integer, nullable=False, unique=True)
    description = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class GraphSnapshot(Base):
    __tablename__ = "graph_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("graph_versions.id"), nullable=False)
    snapshot_timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    description = Column(String(255))

class ConflictingObservation(Base):
    __tablename__ = "conflicting_observations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    claim = Column(String(500), nullable=False)
    existing_fact = Column(JSON)
    new_fact = Column(JSON)
    source = Column(String(255))
    confidence = Column(Float)
    reason = Column(String(500))
    resolution_state = Column(String(50), default="OPEN") # OPEN, CONFIRMED, REJECTED, SUPERSEDED
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class RepairPlan(Base):
    __tablename__ = "repair_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_type = Column(String(100), nullable=False)
    description = Column(String(500))
    status = Column(String(50), default="PENDING") # PENDING, APPROVED, EXECUTED, FAILED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    executed_at = Column(DateTime(timezone=True), nullable=True)

class RepairTask(Base):
    __tablename__ = "repair_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("repair_plans.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(100), nullable=False) # e.g., "MERGE_NODE", "DELETE_EDGE"
    target_id = Column(String(36), nullable=False)
    parameters = Column(JSON)
    status = Column(String(50), default="PENDING")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
