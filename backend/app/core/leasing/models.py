from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.models.base import Base


class Lease(Base):
    """
    PostgreSQL-backed distributed lock (ADR-0059).
    Prevents concurrent workflows from colliding on shared resources.
    """
    __tablename__ = "leases"

    resource_id = Column(String(255), primary_key=True) # e.g. "graph_node_123"
    owner_id = Column(String(255), nullable=False) # workflow_id or agent_id
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    renew_token = Column(String(255), nullable=False) # uuid to prevent stolen releases
    version = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
