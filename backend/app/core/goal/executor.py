import logging

from app.core.goal.models import Goal, GoalState

logger = logging.getLogger(__name__)

class GoalExecutor:
    """
    Hooks into the PlatformScheduler to advance Goals through their lifecycle.
    """
    def __init__(self, agent_registry, workflow_engine):
        self.agent_registry = agent_registry
        self.workflow_engine = workflow_engine

    async def process_goal(self, goal: Goal) -> Goal:
        logger.info(f"Processing Goal {goal.goal_id} in state {goal.state}")

        if goal.state == GoalState.CREATED:
            goal.state = GoalState.PLANNING
            logger.info(f"Goal {goal.goal_id} transitioned to PLANNING.")

        elif goal.state == GoalState.PLANNING:
            agent = self.agent_registry.get_agent(goal.owner_id)
            plan_result = await agent.process_goal(goal.goal_id, {})

            if plan_result["status"] == "planned":
                workflow_def = plan_result["workflow_definition"]
                # Dispatch to workflow engine
                goal.current_workflow_id = f"wf_{goal.goal_id}"
                goal.state = GoalState.EXECUTING
                logger.info(f"Goal {goal.goal_id} transitioned to EXECUTING with workflow {goal.current_workflow_id}.")

        elif goal.state == GoalState.EXECUTING:
            # Check workflow status
            workflow_status = self.workflow_engine.get_status(goal.current_workflow_id)
            if workflow_status == "COMPLETED":
                goal.state = GoalState.REFLECTING
                logger.info(f"Goal {goal.goal_id} transitioned to REFLECTING.")
            elif workflow_status == "FAILED":
                goal.state = GoalState.FAILED

        elif goal.state == GoalState.REFLECTING:
            goal.state = GoalState.EVALUATING
            logger.info(f"Goal {goal.goal_id} transitioned to EVALUATING.")

        elif goal.state == GoalState.EVALUATING:
            goal.state = GoalState.COMPLETED
            logger.info(f"Goal {goal.goal_id} transitioned to COMPLETED.")

        return goal
