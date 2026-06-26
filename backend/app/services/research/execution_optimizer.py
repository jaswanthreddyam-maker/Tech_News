import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ExecutionBudget(BaseModel):
    token_budget: int = 100000
    latency_budget_ms: int = 30000
    cost_budget_usd: float = 0.50
    graph_traversal_budget: int = 1000
    artifact_count_budget: int = 5
    provider_calls_budget: int = 10
    memory_reads_budget: int = 50
    llm_calls_budget: int = 5
    cache_budget: int = 1000

class ExecutionOptimizer:
    """
    Optimizes a Workflow before execution against a strict ExecutionBudget.
    """
    def __init__(self, budget: ExecutionBudget = None):
        self.budget = budget or ExecutionBudget()

    def optimize(self, execution_plan: dict[str, Any]) -> dict[str, Any]:
        """
        Receives a logical execution plan and outputs an optimized version.
        Enforces strict budgets (e.g. max_breadth).
        """
        logger.info("ExecutionOptimizer: Analyzing execution plan against ExecutionBudget.")

        optimized_plan = dict(execution_plan)
        # Apply budget limits. If traversal budget is low, cap max_breadth aggressively.
        max_traversals = self.budget.graph_traversal_budget
        optimized_plan["max_breadth"] = min(execution_plan.get("max_breadth", 100), max(10, max_traversals // 10))

        logger.info(f"ExecutionOptimizer: Plan optimized. Capped breadth at {optimized_plan['max_breadth']}")
        return optimized_plan
