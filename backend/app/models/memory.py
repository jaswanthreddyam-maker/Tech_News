from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String

from app.models.base import Base


class ConversationEpisode(Base):
    __tablename__ = "conversation_episodes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    message = Column(String(2000), nullable=False)
    role = Column(String(20), nullable=False) # USER, ASSISTANT, SYSTEM
    embedding_version = Column(String(50), nullable=True)
    embedding_id = Column(String(100), nullable=True) # Pointer to vector store
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class PreferenceMemory(Base):
    __tablename__ = "preference_memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    key = Column(String(100), nullable=False)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ProceduralMemory(Base):
    __tablename__ = "procedural_memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    workflow_name = Column(String(100), nullable=False)
    config = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
