from typing import Any

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """
    Immutable representation of a step in the execution graph.
    """
    id: str
    action: str
    dependencies: list[str] = Field(default_factory=list)

class ExecutionGraph(BaseModel):
    """
    Immutable execution graph representing the planned sequence of operations.
    Supports linear (A -> B -> C) or DAG topologies based on dependencies.
    """
    steps: list[PlanStep] = Field(default_factory=list)
    version: str = "v1"
    graph_hash: str | None = None

class PlannerCapability:
    """
    Base interface for planning strategies.
    Generates an ExecutionGraph given the context and user request.
    """
    @property
    def capability_name(self) -> str:
        raise NotImplementedError

    async def generate_plan(self, query: str, context: Any) -> ExecutionGraph:
        raise NotImplementedError

class SequentialPlanner(PlannerCapability):
    """
    A basic planner that creates a strict linear sequence: Retrieve -> Reason -> Generate.
    """
    @property
    def capability_name(self) -> str:
        return "SequentialPlanner"

    async def generate_plan(self, query: str, context: Any) -> ExecutionGraph:
        return ExecutionGraph(
            steps=[
                PlanStep(id="step_retrieve", action="retrieve"),
                PlanStep(id="step_reason", action="reason", dependencies=["step_retrieve"]),
                PlanStep(id="step_generate", action="generate", dependencies=["step_reason"])
            ]
        )

class PlannerRegistry:
    def __init__(self):
        self._planners: dict[str, PlannerCapability] = {}

    def register(self, planner: PlannerCapability):
        self._planners[planner.capability_name] = planner

    def get(self, name: str) -> PlannerCapability:
        if name not in self._planners:
            raise KeyError(f"Planner {name} not found in registry.")
        return self._planners[name]
