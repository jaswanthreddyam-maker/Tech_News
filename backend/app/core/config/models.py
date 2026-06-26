from pydantic import BaseModel


class SystemConfiguration(BaseModel):
    """
    Versioned artifact containing OS execution parameters (ADR-0078).
    The kernel reads this instead of hardcoding limits.
    """
    version_id: str
    max_agent_concurrency: int = 10
    default_lease_ttl_seconds: int = 120
    max_workspace_depth: int = 5
    max_retries_per_task: int = 3
    planner_timeout_ms: int = 10000
