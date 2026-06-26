from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CapabilityHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"

class CapabilityHealth(BaseModel):
    status: CapabilityHealthStatus
    latency_ms: float
    availability_pct: float
    error_rate_pct: float
    last_success: str
    version: str
    dependencies: list[str]

class CapabilityIdentity(BaseModel):
    identity_id: str
    owner: str
    permissions: list[str] = Field(default_factory=list)
    secrets_required: list[str] = Field(default_factory=list)
    signing_key_id: str | None = None

class CapabilityContract(BaseModel):
    name: str
    version: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    identity: CapabilityIdentity
    visibility: str = "internal" # internal, partner, public (ADR-0080)


    # Timeouts (ADR-0058)
    soft_timeout_ms: int = 5000
    hard_timeout_ms: int = 10000
    heartbeat_interval_ms: int = 1000
    cancellation_policy: str = "graceful" # graceful, abrupt, none

    # Circuit Breaker config (ADR-0057)
    circuit_breaker_config: dict[str, Any] = Field(
        default_factory=lambda: {"failure_threshold": 5, "rolling_window_ms": 60000, "recovery_timeout_ms": 30000}
    )

    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"retries": 3, "backoff": "exponential"})
    cost_class: str = "low"
    required_policies: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    telemetry_profile: str = "standard"
