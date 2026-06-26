from pydantic import BaseModel


class ExecutionBudget(BaseModel):
    """
    Tracks and limits resource consumption hierarchically.
    """
    money_usd: float = 0.0
    cpu_ms: int = 0
    gpu_ms: int = 0
    memory_mb: int = 0
    storage_mb: int = 0
    network_bytes: int = 0
    time_ms: int = 0

class BudgetConstraints(BaseModel):
    organization_limit: ExecutionBudget
    user_limit: ExecutionBudget
    workflow_limit: ExecutionBudget
    capability_limit: ExecutionBudget
    model_limit: ExecutionBudget
