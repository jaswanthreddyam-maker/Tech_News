import logging

from app.schemas.ai_context import ConversationContext
from app.services.memory.facades import MemoryLayer
from app.services.research.planner_registry import PlannerCapability, PlannerRegistry
from app.services.research.workflow_engine import Workflow, WorkflowStage, WorkflowTask

logger = logging.getLogger(__name__)

class ConversationPlanner:
    """
    Orchestrates the Conversation DAG.
    Strictly adheres to ADR-0035: Memory Retrieval Before Planning.
    """
    def __init__(self):
        self.memory_layer = MemoryLayer()
        self.planner_registry = PlannerRegistry()

    async def plan(self, user_input: str, conversation_id: str, context: ConversationContext) -> Workflow:
        logger.info(f"ConversationPlanner: Initiating planning for {conversation_id}")

        # Step 1: Memory Retrieval (ADR-0035)
        # Fetch episodic, semantic, preference, procedural
        episodic_history = await self.memory_layer.episodic.get_history(conversation_id)
        preferences = await self.memory_layer.preference.get_preferences(context.metadata.user_id if context.metadata.user_id else 0)

        logger.info("ConversationPlanner: Memory Retrieval Complete. Building Planner DAG.")

        # Step 2: Intent Analysis & Planner Selection
        # In reality, this would be an LLM call or intent classifier deciding which planners to invoke.
        # For prototype, we'll compose Timeline and Comparison

        workflow = Workflow("ConversationOrchestrationWorkflow")

        # Stage 1: Invoke specialized planners
        planning_stage = WorkflowStage("PlannerDAGExecution")

        async def run_timeline_planner():
            planner = self.planner_registry.get_best_planner(PlannerCapability.TIMELINE)
            return planner.plan({"query": user_input}, context.snapshot_id)

        async def run_comparison_planner():
            planner = self.planner_registry.get_best_planner(PlannerCapability.COMPARISON)
            return planner.plan({"query": user_input}, context.snapshot_id)

        planning_stage.add_task(WorkflowTask("timeline_planning", run_timeline_planner))
        planning_stage.add_task(WorkflowTask("comparison_planning", run_comparison_planner))

        workflow.add_stage(planning_stage)

        # Additional stages would synthesize the results of the sub-planners
        return workflow
