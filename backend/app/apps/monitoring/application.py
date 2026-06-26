import hashlib
import logging
import uuid

from app.apps.monitoring.artifact_mapper import MonitoringArtifactMapper
from app.apps.monitoring.schemas import CronTriggerEvent
from app.apps.monitoring.viewmodels import AlertViewModel
from app.core.goal.models import Goal
from app.services.capabilities.anomaly_analysis import AnomalyAnalysisCapability
from app.services.capabilities.telemetry import TelemetryCapability

logger = logging.getLogger(__name__)

class AutonomousMonitoringApplication:
    """
    Application layer for autonomous monitoring.
    Consumes capabilities -> Creates Goal -> Awaits Published Artifact -> Maps to ViewModel.
    """
    def __init__(self, platform_scheduler, telemetry_capability: TelemetryCapability, anomaly_capability: AnomalyAnalysisCapability, artifact_repository):
        self.platform_scheduler = platform_scheduler
        self.telemetry_capability = telemetry_capability
        self.anomaly_capability = anomaly_capability
        self.artifact_repository = artifact_repository

    async def process_cron(self, event: CronTriggerEvent) -> AlertViewModel | None:
        logger.info(f"Monitoring App triggered for metric {event.target_metric}")

        # 1. Fetch metrics via Capability Bus (No DB access)
        metrics = await self.telemetry_capability.get_metrics(event.time_window_seconds)

        # 2. Analyze deterministically
        analysis = await self.anomaly_capability.analyze(metrics, event.target_metric)

        if not analysis.get("anomaly"):
            logger.info("No anomaly detected.")
            return None

        logger.warning(f"Anomaly detected in {event.target_metric}: {analysis['deviation']}% deviation.")

        # 3. Formulate Goal
        description = f"Diagnose anomaly in {event.target_metric} (deviation {analysis['deviation']}%). Provide remediation steps."
        fingerprint = hashlib.sha256(description.encode()).hexdigest()

        goal = Goal(
            goal_id=f"goal_monitor_{uuid.uuid4().hex[:8]}",
            owner_id="monitoring_app",
            description=description,
            fingerprint=fingerprint,
            metadata={"analysis": analysis}
        )

        # In a real implementation, we would check if this fingerprint is already running/completed recently.
        # if await self.platform_scheduler.is_goal_deduplicated(fingerprint): return None

        # 4. Dispatch to OS
        await self.platform_scheduler.submit_task(
            capability_name="COORDINATOR",
            version="v1",
            payload={"goal": goal.model_dump()},
            priority=90
        )

        # 5. Await PUBLISHED Artifact (Simulated)
        # In real life, the app might exit here and let another webhook trigger the final step

        # Simulated Artifact (must be PUBLISHED)
        from app.core.artifact.models import Artifact, ArtifactMetadata, ArtifactStatus

        published_artifact = Artifact(
            artifact_id=f"art_{uuid.uuid4().hex[:8]}",
            status=ArtifactStatus.PUBLISHED,
            metadata=ArtifactMetadata(
                version="v1", 
                source_goal=goal.goal_id
            ),
            content={
                "severity": "CRITICAL",
                "metric": event.target_metric,
                "summary": "Root cause identified: Network partition with external AI provider.",
                "evidence": analysis
            }
        )

        # 6. Map to ViewModel
        return MonitoringArtifactMapper.map_to_viewmodel(published_artifact)
