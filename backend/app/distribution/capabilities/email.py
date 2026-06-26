import logging
from typing import Any

from app.distribution.capabilities.base import DistributionCapability, RetryPolicy
from app.models.distribution import DistributionJobStatus, SubjectType

logger = logging.getLogger(__name__)

class EmailCapability(DistributionCapability):
    @property
    def id(self) -> str:
        return "email"

    @property
    def name(self) -> str:
        return "Email Distribution"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 10

    @property
    def supported_subjects(self) -> list[str]:
        return [
            SubjectType.NEWSLETTER.value,
            SubjectType.ARTICLE.value,
            SubjectType.NOTIFICATION.value,
            SubjectType.DIGEST.value,
            SubjectType.INVITATION.value
        ]

    @property
    def retry_policy(self) -> RetryPolicy:
        return RetryPolicy(
            strategy="exponential",
            max_attempts=3,
            initial_delay=60,
            jitter=0.1
        )

    async def supports(self, subject_type: str, subject_data: dict[str, Any]) -> bool:
        return subject_type in self.supported_subjects

    async def build_payload(self, subject_type: str, subject_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "subject": subject_data.get("subject", "Newsletter"),
            "html": subject_data.get("html", ""),
            "text": subject_data.get("text", ""),
            "to": subject_data.get("recipient_email", ""),
            "from_name": subject_data.get("from_name", "Tech News Today"),
            "reply_to": subject_data.get("reply_to", "")
        }

    async def validate(self, job_id: int, payload: dict[str, Any]) -> bool:
        if not payload.get("to"):
            logger.error(f"Job {job_id}: Missing recipient email")
            return False
        return True

    async def resolve(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"Resolving prerequisites for Job {job_id}")
        return payload

    async def preflight(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        # Mock DKIM/SPF / rate limiting
        payload["dkim_signed"] = True
        return payload

    async def distribute(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"Mocking email distribution to {payload.get('to')} for Job {job_id}")
        return {
            "status": DistributionJobStatus.SUCCEEDED,
            "provider_response": {"message_id": f"msg_{job_id}"}
        }

    async def post_delivery(self, job_id: int, result: dict[str, Any]) -> None:
        logger.info(f"Post-delivery hooks for Job {job_id}")

    async def cleanup(self, job_id: int) -> None:
        logger.info(f"Cleaning up resources for Job {job_id}")
