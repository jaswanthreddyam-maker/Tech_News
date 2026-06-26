from dataclasses import dataclass
from enum import Enum
from typing import Optional

class RecoveryState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RECOVERY_PENDING = "RECOVERY_PENDING"
    RECOVERING = "RECOVERING"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"

@dataclass
class RecoveryDecision:
    approved: bool
    reason: str
    recovery_type: str
    cooldown_remaining: int
    consecutive_failures: int
    correlation_id: Optional[str] = None
