from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.user import utc_now


class SearchIndexNode(Base):
    """
    Unified search read-model for all platform entities.
    Enables true hybrid semantic + keyword search.
    """
    __tablename__ = "search_index_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Generic entity reference
    node_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # ARTICLE, WORKSPACE, ENTITY, TOPIC
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Content payload
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)

    # Retrieval columns
    tsvector = mapped_column(TSVECTOR, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)

    # Filtering / Facets
    metadata_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    workspace_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    visibility: Mapped[str] = mapped_column(String(50), nullable=False, default="PUBLIC") # PUBLIC, PRIVATE

    # Embedding metadata
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, default="text-embedding-3-small")
    embedding_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")
    embedding_generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    content_checksum: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class GenerationTelemetry(Base):
    """
    Tracks AI generation metrics across all capabilities (RAG, Chat, Copilot).
    """
    __tablename__ = "generation_telemetry"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    capability_name: Mapped[str] = mapped_column(String(100), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=True)

    # Latencies
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    retrieval_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    prompt_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    generation_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    validation_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    stream_latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Model & tokens
    provider_name: Mapped[str] = mapped_column(String(100), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # State
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    retrievers_used: Mapped[list] = mapped_column(JSONB, default=list)
    context_chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # AI capability specifics
    tool_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    pipeline_version: Mapped[str] = mapped_column(String(50), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=True)
    profile: Mapped[str] = mapped_column(String(50), nullable=True)

    # Validation
    is_valid_citations: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class AgentTelemetry(Base):
    """
    Operational observability for the Agent Runtime loop.
    Separates high-level agentic metrics from low-level Generation metrics.
    """
    __tablename__ = "agent_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    agent: Mapped[str] = mapped_column(String(100), nullable=False)
    planner: Mapped[str] = mapped_column(String(100), nullable=False)
    plan_version: Mapped[str] = mapped_column(String(50), nullable=True)
    execution_graph_version: Mapped[str] = mapped_column(String(50), nullable=True)
    memory_provider: Mapped[str] = mapped_column(String(100), nullable=True)

    step_count: Mapped[int] = mapped_column(Integer, default=0)
    generation_calls: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    recovery_count: Mapped[int] = mapped_column(Integer, default=0)
    reflection_count: Mapped[int] = mapped_column(Integer, default=0)

    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    finish_reason: Mapped[str] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
