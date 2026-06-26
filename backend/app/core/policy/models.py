from typing import Any

from pydantic import BaseModel


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str | None = None
    violated_policy: str | None = None
    severity: str = "high"
    metadata: dict[str, Any] = {}
    trace_id: str | None = None

class BasePolicy:
    @property
    def name(self) -> str:
        raise NotImplementedError()

    @property
    def priority(self) -> int:
        return 50

    @property
    def stop_on_failure(self) -> bool:
        return True

    @property
    def category(self) -> str:
        return "general"

    @property
    def version(self) -> str:
        return "v1"

    async def evaluate(self, context: Any) -> PolicyDecision:
        raise NotImplementedError()
