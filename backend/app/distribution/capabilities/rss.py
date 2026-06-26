from typing import Any

from app.distribution.capabilities.base import DistributionCapability, RetryPolicy
from app.models.distribution import DistributionJobStatus


class RSSCapability(DistributionCapability):
    @property
    def id(self) -> str:
        return "RSS"

    @property
    def name(self) -> str:
        return "RSS Feed Distribution"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def priority(self) -> int:
        return 10

    @property
    def supported_subjects(self) -> list[str]:
        return ["ARTICLE"]

    @property
    def retry_policy(self) -> RetryPolicy:
        return RetryPolicy(
            max_attempts=3,
            strategy="exponential",
            initial_delay=30
        )

    async def supports(self, subject_type: str, subject_data: dict[str, Any]) -> bool:
        return subject_type in self.supported_subjects

    async def build_payload(self, subject_type: str, subject_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": subject_data.get("title", ""),
            "url": subject_data.get("url", ""),
            "summary": subject_data.get("summary", ""),
            "published_at": subject_data.get("published_at", "")
        }

    async def distribute(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        # Dummy implementation for distribution
        # In reality, this would write to an RSS XML file or update a cache
        return {
            "status": DistributionJobStatus.SUCCESS,
            "provider_response": {"message": "RSS feed updated successfully"}
        }
