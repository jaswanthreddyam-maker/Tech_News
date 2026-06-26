from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class ApprovalPolicyType(str, Enum):
    AUTO = "AUTO"
    HUMAN = "HUMAN"
    QUORUM = "QUORUM"
    EXTERNAL = "EXTERNAL"

class ApprovalPolicy(BaseModel):
    policy_id: str
    type: ApprovalPolicyType
    required_roles: list[str] = Field(default_factory=list)
    quorum_size: int = 1
    external_webhook_url: str | None = None

class ApprovalRequest(BaseModel):
    """
    Formal boundary between proposed changes and applied changes (ADR-0060).
    """
    request_id: str
    target_resource_type: str # e.g. KNOWLEDGE_GRAPH, MEMORY
    target_resource_id: str
    proposed_payload: dict[str, Any]
    policy_id: str
    state: ApprovalState = ApprovalState.PENDING
    approvers: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
