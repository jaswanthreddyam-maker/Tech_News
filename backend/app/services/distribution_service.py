import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.distribution.registry import registry

# Ensure capabilities are registered
from app.distribution.setup import register_all_capabilities
from app.models.distribution import DeliveryReport, DistributionJob, DistributionJobStatus, DistributionManifest

register_all_capabilities()

logger = logging.getLogger(__name__)

class DistributionPlanner:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def plan_distribution(
        self, 
        publication_record_id: int, 
        subject_type: str, 
        subject_id: str, 
        subject_data: dict[str, Any],
        audience_snapshot: dict[str, Any] | None = None,
        content_checksum: str | None = None
    ) -> DistributionManifest:
        """
        Creates a DistributionManifest and fans out into DistributionJobs based on active capabilities.
        """
        active_capabilities = registry.active()
        channels = []
        for capability in active_capabilities:
            if await capability.supports(subject_type, subject_data):
                channels.append(capability.id)

        manifest = DistributionManifest(
            publication_record_id=publication_record_id,
            subject_type=subject_type,
            channels=channels,
            audience=audience_snapshot,
            content_checksum=content_checksum
        )
        self.db.add(manifest)
        await self.db.flush()

        jobs_created = []

        for capability in active_capabilities:
            if await capability.supports(subject_type, subject_data):
                payload = await capability.build_payload(subject_type, subject_data)
                job = DistributionJob(
                    manifest_id=manifest.id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    channel=capability.id,
                    status=DistributionJobStatus.QUEUED,
                    payload=payload
                )
                self.db.add(job)
                jobs_created.append(job)

        await self.db.commit()
        return manifest


class DistributionExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_job(self, job_id: int) -> DeliveryReport:
        """
        Executes a single DistributionJob using the appropriate capability.
        """
        stmt = select(DistributionJob).where(DistributionJob.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalars().first()

        if not job:
            raise ValueError("Distribution job not found")

        capability = registry.get(job.channel)
        if not capability:
            job.status = DistributionJobStatus.FAILED
            report = DeliveryReport(
                job_id=job.id,
                status=DistributionJobStatus.FAILED,
                error="Capability not found in registry",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            self.db.add(report)
            await self.db.commit()
            return report

        job.status = DistributionJobStatus.RUNNING
        job.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        started_at = datetime.now(timezone.utc)
        error_message = None
        provider_response = None
        final_status = DistributionJobStatus.FAILED

        try:
            job.status = DistributionJobStatus.VALIDATING
            job.updated_at = datetime.now(timezone.utc)
            await self.db.commit()

            is_valid = await capability.validate(job.id, job.payload)
            if not is_valid:
                final_status = DistributionJobStatus.SKIPPED
                error_message = "Skipped by capability validation"
                result = {"status": final_status, "error": error_message}
            else:
                job.payload = await capability.resolve(job.id, job.payload)

                job.status = DistributionJobStatus.PREFLIGHT
                job.updated_at = datetime.now(timezone.utc)
                await self.db.commit()

                job.payload = await capability.preflight(job.id, job.payload)

                job.status = DistributionJobStatus.RUNNING
                job.updated_at = datetime.now(timezone.utc)
                await self.db.commit()

                result = await capability.distribute(job.id, job.payload)
                final_status = result.get("status", DistributionJobStatus.SUCCEEDED)
                provider_response = result.get("provider_response")
                error_message = result.get("error")

                await capability.post_delivery(job.id, result)
        except Exception as e:
            error_message = str(e)
            logger.exception(f"Error distributing job {job.id} via {capability.id}")
        finally:
            try:
                await capability.cleanup(job.id)
            except Exception as cleanup_err:
                logger.error(f"Error in cleanup for job {job.id}: {cleanup_err}")

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        job.status = final_status
        job.updated_at = completed_at

        report = DeliveryReport(
            job_id=job.id,
            status=final_status,
            duration_ms=duration_ms,
            error=error_message,
            provider_response=provider_response,
            started_at=started_at,
            completed_at=completed_at
        )
        self.db.add(report)
        await self.db.commit()

        return report
