import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class PlannerCapability(str, Enum):
    TIMELINE = "TIMELINE"
    SUMMARY = "SUMMARY"
    COMPARISON = "COMPARISON"
    RESEARCH = "RESEARCH"
    CHAT = "CHAT"
    ENTITY = "ENTITY"
    SEARCH = "SEARCH"
    MULTI_HOP = "MULTI_HOP"
    GRAPH = "GRAPH"

class BasePlanner:
    @property
    def capabilities(self) -> list[PlannerCapability]:
        return []

    def plan(self, intent_data: dict[str, Any], snapshot_id: int) -> Any:
        raise NotImplementedError()

class TimelinePlanner(BasePlanner):
    @property
    def capabilities(self) -> list[PlannerCapability]:
        return [PlannerCapability.TIMELINE, PlannerCapability.ENTITY]

    def plan(self, intent_data: dict[str, Any], snapshot_id: int) -> Any:
        return None

class ComparisonPlanner(BasePlanner):
    @property
    def capabilities(self) -> list[PlannerCapability]:
        return [PlannerCapability.COMPARISON]

    def plan(self, intent_data: dict[str, Any], snapshot_id: int) -> Any:
        return None

class PlannerRegistry:
    """
    Manages planners based on PlannerCapabilities.
    Supports recursive planner composition.
    """
    def __init__(self):
        self._planners: list[BasePlanner] = [
            TimelinePlanner(),
            ComparisonPlanner()
        ]

    def get_planners_by_capability(self, capability: PlannerCapability) -> list[BasePlanner]:
        return [p for p in self._planners if capability in p.capabilities]

    def get_best_planner(self, capability: PlannerCapability) -> BasePlanner:
        planners = self.get_planners_by_capability(capability)
        if not planners:
            raise ValueError(f"No planner found for capability {capability.value}")
        return planners[0]
