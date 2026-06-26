from enum import Enum

from pydantic import BaseModel


class ConsistencyMode(str, Enum):
    EXACTLY_ONCE = "EXACTLY_ONCE"
    AT_LEAST_ONCE = "AT_LEAST_ONCE"
    AT_MOST_ONCE = "AT_MOST_ONCE"

class ProjectionPolicy(BaseModel):
    consistency: ConsistencyMode = ConsistencyMode.EXACTLY_ONCE
    priority: str = "NORMAL"
    batch_size: int = 100
    parallelism: int = 1
    replay_allowed: bool = True
    checkpoint_enabled: bool = True
    telemetry_enabled: bool = True
    timeout_seconds: int = 30
