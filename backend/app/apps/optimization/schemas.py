from pydantic import BaseModel


class OptimizationTriggerEvent(BaseModel):
    """
    Event received from a cron dispatcher or monitoring alert.
    """
    job_id: str
    target_component: str
    reason: str
