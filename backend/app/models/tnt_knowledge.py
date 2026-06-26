from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EntityNode(Base):
    __tablename__ = "tnt_entity_nodes"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Relationships
    relationships_as_source = relationship("RelationshipEdge", foreign_keys="[RelationshipEdge.source_id]", back_populates="source_node")
    relationships_as_target = relationship("RelationshipEdge", foreign_keys="[RelationshipEdge.target_id]", back_populates="target_node")
    article_links = relationship("ArticleEntityLink", back_populates="entity")


class TopicNode(Base):
    __tablename__ = "tnt_topic_nodes"

    name: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    taxonomy_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Relationships
    article_links = relationship("ArticleTopicLink", back_populates="topic")


class ArticleEntityLink(Base):
    __tablename__ = "tnt_article_entities"
    __table_args__ = (UniqueConstraint("article_id", "entity_id", name="uq_tnt_article_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[str] = mapped_column(String(64), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), ForeignKey("tnt_entity_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    entity = relationship("EntityNode", back_populates="article_links")


class ArticleTopicLink(Base):
    __tablename__ = "tnt_article_topics"
    __table_args__ = (UniqueConstraint("article_id", "topic_name", name="uq_tnt_article_topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[str] = mapped_column(String(64), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_name: Mapped[str] = mapped_column(String(255), ForeignKey("tnt_topic_nodes.name", ondelete="CASCADE"), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    topic = relationship("TopicNode", back_populates="article_links")


class TimelineEventNode(Base):
    __tablename__ = "tnt_timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[str] = mapped_column(String(64), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(50), nullable=False) # Keep as string for partial dates e.g. "2026-07"
    certainty: Mapped[str] = mapped_column(String(50), nullable=False)
    entities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list) # Store entity IDs
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RelationshipEdge(Base):
    __tablename__ = "tnt_relationship_edges"
    __table_args__ = (UniqueConstraint("article_id", "source_id", "predicate", "target_id", name="uq_tnt_relationship"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[str] = mapped_column(String(64), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), ForeignKey("tnt_entity_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    predicate: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(255), ForeignKey("tnt_entity_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    source_node = relationship("EntityNode", foreign_keys=[source_id], back_populates="relationships_as_source")
    target_node = relationship("EntityNode", foreign_keys=[target_id], back_populates="relationships_as_target")
