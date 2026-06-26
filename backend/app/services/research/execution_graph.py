import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

class RetrievalTask:
    def __init__(self, name: str, action: Callable[..., Awaitable[Any]], dependencies: list[str] | None = None):
        self.name = name
        self.action = action
        self.dependencies = dependencies or []
        self.result = None
        self.status = "PENDING"

class ExecutionGraph:
    """
    Executes a DAG of RetrievalTasks concurrently.
    """
    def __init__(self):
        self.tasks: dict[str, RetrievalTask] = {}

    def add_task(self, task: RetrievalTask):
        self.tasks[task.name] = task

    async def execute(self) -> dict[str, Any]:
        """
        Executes the DAG. In a real implementation, this would use asyncio.gather
        based on dependency resolution. For prototyping, we do a topological sort.
        """
        logger.info(f"ExecutionGraph: Starting execution of {len(self.tasks)} tasks.")

        results = {}
        pending = list(self.tasks.values())

        while pending:
            # Find tasks with no pending dependencies
            ready = [
                t for t in pending 
                if all(dep in results for dep in t.dependencies)
            ]

            if not ready:
                raise RuntimeError("ExecutionGraph: Cycle detected or unresolvable dependencies.")

            # Execute ready tasks concurrently
            tasks_to_run = [t.action() for t in ready]
            batch_results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

            for t, res in zip(ready, batch_results):
                if isinstance(res, Exception):
                    t.status = "FAILED"
                    logger.error(f"Task {t.name} failed: {res}")
                    raise res # ADR-0026: Evidence before synthesis. We fail fast.
                else:
                    t.status = "COMPLETED"
                    t.result = res
                    results[t.name] = res
                    pending.remove(t)

        logger.info("ExecutionGraph: All tasks completed successfully.")
        return results
