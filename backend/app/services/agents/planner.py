import logging
from typing import Any, Protocol

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class PlannerResult(BaseModel):
    """
    The deterministic output of a PlanningStrategy (ADR-0071).
    Planners never mutate the workspace; they only return this result.
    """
    tasks: list[Any]
    branches: list[Any]
    risks: list[str]
    assumptions: list[str]
    confidence: float
    expected_cost: float
    expected_duration: int
    required_budget: float
    required_capabilities: list[str]
    success_criteria: list[str]
    failure_modes: list[str]
    rollback_plan: list[str]

class PlanningStrategy(Protocol):
    """
    Protocol for pluggable planning algorithms (ADR-0071).
    Examples: ReAct, TreeOfThoughts, MCTS.
    """
    async def plan(self, goal: Any, workspace_snapshot: Any, budget: Any) -> PlannerResult:
        ...
