from typing import Any

from pydantic import BaseModel


class AlertViewModel(BaseModel):
    """
    The UI or downstream alerting system consumes this ViewModel. (ADR-0076)
    """
    alert_id: str
    severity: str
    metric: str
    summary: str
    source_goal: str
    evidence: dict[str, Any]
