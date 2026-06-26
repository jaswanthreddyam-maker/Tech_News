from typing import Any

from pydantic import BaseModel, Field

from app.core.capability.models import CapabilityIdentity


class AgentProfile(BaseModel):
    name: str
    description: str
    identity: CapabilityIdentity
    allowed_intents: list[str] = Field(default_factory=list)

class ExecutionMetrics(BaseModel):
    wall_duration_ms: int = 0
    cpu_duration_ms: int = 0
    token_input: int = 0
    token_output: int = 0
    tool_calls: int = 0
    retry_count: int = 0
    lease_extensions: int = 0
    cost_usd: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    planner_version: str | None = None
    model_version: str | None = None
    snapshot_id: str

class AgentExecutionResult(BaseModel):
    entries: list[dict[str, Any]] # Will be mapped to WorkspaceEntry
    artifacts: list[dict[str, Any]]
    evidence: dict[str, Any]
    metrics: ExecutionMetrics

class AgentInterface:
    @property
    def profile(self) -> AgentProfile:
        raise NotImplementedError()

    async def process_goal(
        self, 
        goal: Any, 
        workspace_snapshot: Any, 
        budget: Any, 
        policies: Any
    ) -> AgentExecutionResult:
        """
        Agents consume a snapshot and emit new append-only workspace entries.
        (ADR-0065, ADR-0067)
        """
        raise NotImplementedError()
