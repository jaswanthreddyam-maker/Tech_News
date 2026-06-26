from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentLifecycle(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    WAITING_FOR_TOOL = "WAITING_FOR_TOOL"
    RESUMING = "RESUMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class AgentManifest(BaseModel):
    agent: str
    agent_version: str = "1.0"
    planner: str = "sequential"
    planner_version: str = "1"
    memory: str = "conversation"
    generation_profile: str = "Balanced"
    capability: str = "AgentCapability"
    recovery: str = "FallbackProvider"
    reflection: str = "NoReflection"
    tools: list[str] = Field(default_factory=list)

class ExecutionManifest(BaseModel):
    """
    Immutable snapshot of an execution run allowing perfect reproduction.
    """
    execution_id: str
    agent_manifest: AgentManifest
    generation_manifest: dict[str, Any] | None = None
    execution_graph_hash: str | None = None
    runtime_version: str = "1.0"
    planner_version: str = "1.0"
    memory_version: str = "1.0"
    pipeline_version: str = "1.0"

class AgentSession(BaseModel):
    """
    Operational state representing a long-lived conversation or task context.
    May contain multiple executions.
    """
    id: str
    user_id: int | None = None
    workspace_id: int | None = None
    status: str = "ACTIVE" # ACTIVE, ARCHIVED

class ExecutionState(BaseModel):
    """
    Mutable state of an execution run, tracking token usage and outputs.
    """
    current_step_id: str | None = None
    results: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    generation_calls: int = 0
    tool_calls: int = 0

class AgentExecution(BaseModel):
    """
    Operational state for a single agent run (e.g., fulfilling one user request).
    """
    id: str
    session_id: str
    manifest: AgentManifest
    status: AgentLifecycle = AgentLifecycle.CREATED
    state: ExecutionState = Field(default_factory=ExecutionState)
