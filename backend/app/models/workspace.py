import enum
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings


class WorkspaceEventType(str, enum.Enum):
    ARTICLE_PINNED = "ARTICLE_PINNED"
    ARTICLE_UNPINNED = "ARTICLE_UNPINNED"
    NOTE_CREATED = "NOTE_CREATED"
    NOTE_UPDATED = "NOTE_UPDATED"
    NOTE_DELETED = "NOTE_DELETED"
    CHAT_STARTED = "CHAT_STARTED"
    CHAT_COMPLETED = "CHAT_COMPLETED"
    COMPARISON_CREATED = "COMPARISON_CREATED"
    WORKSPACE_CREATED = "WORKSPACE_CREATED"
    WORKSPACE_RENAMED = "WORKSPACE_RENAMED"
    EXPORT_CREATED = "EXPORT_CREATED"


class NoteChangeType(str, enum.Enum):
    MANUAL = "MANUAL"
    AI_EXPAND = "AI_EXPAND"
    AI_REFINE = "AI_REFINE"
    AI_SUMMARIZE = "AI_SUMMARIZE"
    RESTORE = "RESTORE"


class NotebookOperation(str, enum.Enum):
    SUMMARIZE = "SUMMARIZE"
    EXPAND = "EXPAND"
    REFINE = "REFINE"
    REWRITE = "REWRITE"
    OUTLINE = "OUTLINE"
    FIND_CITATIONS = "FIND_CITATIONS"


from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "user" or "anonymous"
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # user_id or client_id
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    articles = relationship("WorkspaceArticle", back_populates="workspace", cascade="all, delete-orphan")
    conversations = relationship("WorkspaceConversation", back_populates="workspace", cascade="all, delete-orphan")
    notes = relationship("WorkspaceNote", back_populates="workspace", cascade="all, delete-orphan")
    activities = relationship("WorkspaceActivity", back_populates="workspace", cascade="all, delete-orphan")
    digests = relationship("WorkspaceDigest", back_populates="workspace", cascade="all, delete-orphan")
    drafts = relationship("EditorialDraft", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceArticle(Base):
    __tablename__ = "workspace_articles"
    __table_args__ = (UniqueConstraint("workspace_id", "article_id", name="uq_workspace_article"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    workspace = relationship("Workspace", back_populates="articles")


class WorkspaceConversation(Base):
    __tablename__ = "workspace_conversations"
    __table_args__ = (UniqueConstraint("workspace_id", "conversation_id", name="uq_workspace_conversation"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # UUID stored as string from ConversationPlatform
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    workspace = relationship("Workspace", back_populates="conversations")


class WorkspaceNote(Base):
    __tablename__ = "workspace_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_ai_modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    embedding_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    embedding = mapped_column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)
    embedding_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    embedding_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="notes")
    versions = relationship("WorkspaceNoteVersion", back_populates="note", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "ix_workspace_notes_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class WorkspaceNoteVersion(Base):
    __tablename__ = "workspace_note_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    note_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspace_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "MANUAL", "AI_EXPAND"
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "user", "anonymous", "ai"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    note = relationship("WorkspaceNote", back_populates="versions")


class WorkspaceActivity(Base):
    __tablename__ = "workspace_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Structured logging
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "user", "anonymous", "system"
    resource_type: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g. "article", "note", "conversation"
    resource_id: Mapped[str] = mapped_column(String(255), nullable=True)  # ID of the resource

    # Flexible metadata
    metadata_payload: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="activities")


class WorkspaceDigest(Base):
    __tablename__ = "workspace_digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )

    since_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    until_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="COMPLETED"
    )  # GENERATING, COMPLETED, FAILED

    metadata_payload: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)

    generation_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    # Relationships
    workspace = relationship("Workspace", back_populates="digests")
