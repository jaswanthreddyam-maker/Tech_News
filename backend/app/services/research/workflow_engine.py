import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

class WorkflowTask:
    def __init__(self, name: str, action: Callable[..., Awaitable[Any]], dependencies: list[str] | None = None):
        self.name = name
        self.action = action
        self.dependencies = dependencies or []

class WorkflowStage:
    def __init__(self, name: str):
        self.name = name
        self.tasks: list[WorkflowTask] = []

    def add_task(self, task: WorkflowTask):
        self.tasks.append(task)

class Workflow:
    """Immutable definition of the execution graph."""
    def __init__(self, name: str):
        self.name = name
        self.stages: list[WorkflowStage] = []
        self._tasks: dict[str, WorkflowTask] = {}

    def add_stage(self, stage: WorkflowStage):
        self.stages.append(stage)
        for task in stage.tasks:
            self._tasks[task.name] = task

class WorkflowEngine:
    """
    Executes a Workflow idempotently and safely. 
    ADR-0027: Execution Is Idempotent.
    """
    def __init__(self):
        pass

    async def execute(self, workflow: Workflow, previous_state: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Executes the Workflow. If previous_state is provided, safely resumes 
        by skipping already completed tasks.
        """
        logger.info(f"WorkflowEngine: Starting execution of Workflow '{workflow.name}'")

        state = previous_state or {}
        results = state.get("results", {})

        for stage in workflow.stages:
            logger.info(f"WorkflowEngine: Entering Stage '{stage.name}'")
            pending_tasks = []

            for task in stage.tasks:
                if task.name in results:
                    logger.info(f"WorkflowEngine: Skipping {task.name} (already completed in previous attempt).")
                    continue
                pending_tasks.append(task)

            if not pending_tasks:
                continue

            # Execute pending tasks in the current stage concurrently
            # In a full DAG, this would resolve dependencies dynamically.
            # Here we assume tasks within a stage are independent.
            tasks_to_run = [t.action() for t in pending_tasks]
            batch_results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

            for t, res in zip(pending_tasks, batch_results):
                if isinstance(res, Exception):
                    logger.error(f"WorkflowEngine: Task {t.name} failed: {res}")
                    raise res # Fails the entire attempt, allowing resumption later
                else:
                    results[t.name] = res

        logger.info(f"WorkflowEngine: Workflow '{workflow.name}' completed successfully.")
        return results

    async def resume(self, workflow: Workflow, execution_attempt_id: int):
        # Fetches attempt state from DB and calls execute()
        pass
