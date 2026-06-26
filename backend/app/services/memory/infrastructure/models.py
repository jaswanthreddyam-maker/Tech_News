from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.models.base import Base


class MemoryIndex(Base):
    """
    Decouples metadata from dumb vector storage.
    """
    __tablename__ = "memory_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    embedding_id = Column(String(100), nullable=False, index=True) # ID in PgVector/Pinecone
    memory_id = Column(String(100), nullable=False) # Logical memory UUID
    memory_type = Column(String(50), nullable=False) # EPISODIC, SEMANTIC, PROCEDURAL, PREFERENCE
    owner_id = Column(String(100), nullable=False) # User ID or Agent ID

    version = Column(String(50), default="v1")
    confidence = Column(Float, default=1.0)
    ttl_expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
