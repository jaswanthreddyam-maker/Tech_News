from typing import Any

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    query: str
    workspace_id: int | None = None
    language: str = "en"
    stream: bool = False
    filters: dict[str, Any] = Field(default_factory=dict)
    conversation_history: list[dict[str, str]] = Field(default_factory=list)

class GenerationTelemetryResponse(BaseModel):
    total_latency_ms: int
    retrieval_latency_ms: int

class GenerationResponse(BaseModel):
    answer: str
    citations: dict[str, Any] = Field(default_factory=dict)
    retrieved_documents: list[dict[str, Any]] = Field(default_factory=list)
    provider: str
    model: str
    telemetry: GenerationTelemetryResponse
