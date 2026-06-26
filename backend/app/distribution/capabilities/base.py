from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel


class RetryPolicy(BaseModel):
    max_attempts: int = 5
    strategy: Literal["fixed", "linear", "exponential"] = "exponential"
    initial_delay: int = 30  # seconds
    maximum_delay: int = 3600  # seconds
    jitter: bool = True

class DistributionCapability(ABC):
    """Base contract for all distribution channels."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the capability (e.g., 'rss', 'newsletter')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Capability version."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Execution priority (lower is earlier)."""
        pass

    @property
    @abstractmethod
    def supported_subjects(self) -> list[str]:
        """List of supported subject types (e.g., ['ARTICLE', 'NEWSLETTER'])."""
        pass

    @property
    @abstractmethod
    def retry_policy(self) -> RetryPolicy:
        """Retry strategy for failed deliveries."""
        pass

    @property
    def enabled(self) -> bool:
        """Whether this capability is active."""
        return True

    @abstractmethod
    async def supports(self, subject_type: str, subject_data: dict[str, Any]) -> bool:
        """Check if this capability supports the given subject."""
        pass

    @abstractmethod
    async def build_payload(self, subject_type: str, subject_data: dict[str, Any]) -> dict[str, Any]:
        """Builds the channel-specific payload from generic data."""
        pass

    async def validate(self, job_id: int, payload: dict[str, Any]) -> bool:
        """Validates payload or recipient before preflight. Return False to skip distribution."""
        return True

    async def resolve(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Resolves capability-specific prerequisites (e.g. fetching external tokens)."""
        return payload

    async def preflight(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Pre-checks, DKIM/SPF sign, rate limits, etc. Returns updated payload."""
        return payload

    @abstractmethod
    async def distribute(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Executes the actual distribution and returns a result dict."""
        pass

    async def post_delivery(self, job_id: int, result: dict[str, Any]) -> None:
        """Handles bounces, opens, clicks tracking registration post-delivery."""
        return None

    async def cleanup(self, job_id: int) -> None:
        """Always executes after distribution (success or failure) to release resources."""
        return None

    async def verify(self, job_id: int) -> bool:
        """Optional verification step after distribution."""
        return True

    async def rollback(self, job_id: int) -> bool:
        """Optional rollback if something fails."""
        return True
