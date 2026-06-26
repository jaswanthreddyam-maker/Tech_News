from typing import Any

from pydantic import BaseModel


class OptimizationProposalViewModel(BaseModel):
    """
    The UI or Admin Dashboard consumes this ViewModel. (ADR-0076)
    """
    proposal_id: str
    component: str
    status: str
    proposed_changes: dict[str, Any]
    expected_impact: str
    source_goal: str
