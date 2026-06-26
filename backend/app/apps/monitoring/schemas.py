from pydantic import BaseModel


class CronTriggerEvent(BaseModel):
    """
    Event received from a cron dispatcher to trigger monitoring.
    """
    job_id: str
    target_metric: str
    time_window_seconds: int = 3600
