from typing import Any

from pydantic import BaseModel, Field


class RetrievalContext(BaseModel):
    """
    State from the retrieval stage (Search, Graph, Workspace, etc.).
    """
    query: str
    workspace_id: int | None = None
    language: str = "en"
    country: str | None = None
    visibility: str = "PUBLIC"
    permissions: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    embedding_version: str = "v1.0"

class AIContext(RetrievalContext):
    """
    The full unified context spanning the entire generation pipeline.
    Passed through ContextCollector -> PromptBuilder -> LLM -> Validator.
    """
    user_id: int | None = None
    session_id: str | None = None
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    persona: str | None = None
    organization_id: int | None = None

    # Accumulated during pipeline execution
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)
    compressed_chunks: list[dict[str, Any]] = Field(default_factory=list)
    citations: dict[str, Any] = Field(default_factory=dict)

class CapabilityContext(AIContext):
    """
    Extends AIContext to hold specific intelligence capability metadata.
    """
    capability_name: str
    profile_version: str = "v1"
    prompt_version: str = "v1"
    pipeline_version: str = "v1"
    feature_flags: list[str] = Field(default_factory=list)
    experiment_variant: str | None = None
