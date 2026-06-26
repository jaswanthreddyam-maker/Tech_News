import logging
from typing import Any

from app.services.research.planner_registry import BasePlanner
from app.services.research.planners.comparison_dimensions import (
    ComparisonDimension,
    FinancialDimension,
    LegalDimension,
    TimelineDimension,
)
from app.services.research.workflow_engine import Workflow, WorkflowStage, WorkflowTask

logger = logging.getLogger(__name__)

class ComparisonExecutionPlan:
    def __init__(self, intent_data: dict[str, Any], dimensions: list[ComparisonDimension]):
        self.intent_data = intent_data
        self.dimensions = dimensions

    def build_workflow(self) -> Workflow:
        workflow = Workflow("ComparisonWorkflow")

        # Stage 1: Resolve Entities
        resolve_stage = WorkflowStage("ResolveEntities")

        async def resolve_a(): return "Node_A"
        async def resolve_b(): return "Node_B"

        task_a = WorkflowTask("resolve_a", resolve_a)
        task_b = WorkflowTask("resolve_b", resolve_b)
        resolve_stage.add_task(task_a)
        resolve_stage.add_task(task_b)
        workflow.add_stage(resolve_stage)

        # Stage 2: Dimension Comparisons
        compare_stage = WorkflowStage("CompareDimensions")
        for dim in self.dimensions:
            async def run_dim(d=dim):
                return d.compare("Node_A", "Node_B", 1)
            task = WorkflowTask(f"compare_{dim.name.lower()}", run_dim, dependencies=["resolve_a", "resolve_b"])
            compare_stage.add_task(task)

        workflow.add_stage(compare_stage)
        return workflow

class ComparisonPlanner(BasePlanner):
    def __init__(self):
        self.dimensions: list[ComparisonDimension] = [
            FinancialDimension(),
            LegalDimension(),
            TimelineDimension()
        ]

    def plan(self, intent_data: dict[str, Any], snapshot_id: int) -> ComparisonExecutionPlan:
        logger.info("ComparisonPlanner: Generating ComparisonExecutionPlan.")
        return ComparisonExecutionPlan(intent_data, self.dimensions)
