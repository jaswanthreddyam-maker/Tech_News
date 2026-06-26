import hashlib
import logging
import uuid
from typing import Any

from app.apps.optimization.artifact_mapper import OptimizationArtifactMapper
from app.apps.optimization.schemas import OptimizationTriggerEvent
from app.apps.optimization.viewmodels import OptimizationProposalViewModel
from app.core.artifact.models import Artifact, ArtifactMetadata, ArtifactStatus
from app.core.goal.models import Goal

logger = logging.getLogger(__name__)

class SelfOptimizationApplication:
    """
    Application layer for OS Self-Optimization.
    Creates an Optimization Goal -> OS executes it -> Yields a SystemConfiguration Artifact.
    """
    def __init__(self, platform_scheduler, artifact_repository):
        self.platform_scheduler = platform_scheduler
        self.artifact_repository = artifact_repository

    async def process_trigger(self, event: OptimizationTriggerEvent) -> OptimizationProposalViewModel | None:
        logger.info(f"Self-Optimization App triggered for {event.target_component}. Reason: {event.reason}")

        # 1. Formulate Goal
        description = f"Propose an optimization plan for {event.target_component} to address: {event.reason}"
        fingerprint = hashlib.sha256(description.encode()).hexdigest()

        goal = Goal(
            goal_id=f"goal_opt_{uuid.uuid4().hex[:8]}",
            owner_id="optimization_app",
            description=description,
            fingerprint=fingerprint,
            metadata={"target": event.target_component}
        )

        # 2. Dispatch to OS
        await self.platform_scheduler.submit_task(
            capability_name="COORDINATOR",
            version="v1",
            payload={"goal": goal.model_dump()},
            priority=80
        )

        # 3. Await Artifact (Simulated)
        # Note: Optimization proposals often pause at PENDING_APPROVAL based on the Policy Engine.
        # Applications can map PENDING_APPROVAL artifacts to show them in an Admin Dashboard.

        simulated_artifact = Artifact(
            artifact_id=f"art_cfg_{uuid.uuid4().hex[:8]}",
            status=ArtifactStatus.PENDING_APPROVAL,
            metadata=ArtifactMetadata(
                version="v2", 
                type="system_configuration",
                source_goal=goal.goal_id
            ),
            content={
                "component": "PlatformScheduler",
                "proposed_changes": {
                    "max_agent_concurrency": 60, # Triggers OptimizationApprovalPolicy
                    "planner_timeout_ms": 15000
                },
                "expected_impact": "Reduces goal queue backpressure by 40%."
            }
        )

        # 4. Map to ViewModel
        return OptimizationArtifactMapper.map_to_viewmodel(simulated_artifact)

    async def on_config_published(self, event: Any):
        """
        Configuration Feedback Loop (ADR-0055).
        Triggered when a configuration artifact is PUBLISHED.
        Schedules an Evaluation Goal to mathematically prove the impact.
        """
        config_artifact_id = event.get("artifact_id")
        logger.info(f"Scheduling evaluation for published config {config_artifact_id}")

        eval_goal = Goal(
            goal_id=f"goal_eval_{uuid.uuid4().hex[:8]}",
            owner_id="optimization_app",
            description=f"Evaluate telemetry impact of config {config_artifact_id} after 24 hours.",
            fingerprint=hashlib.sha256(f"eval_{config_artifact_id}".encode()).hexdigest(),
            metadata={"target_config": config_artifact_id, "delay_hours": 24}
        )

        await self.platform_scheduler.submit_task(
            capability_name="COORDINATOR",
            version="v1",
            payload={"goal": eval_goal.model_dump()},
            priority=30 # Lower priority for evaluations
        )
