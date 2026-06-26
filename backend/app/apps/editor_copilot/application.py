import logging

from app.apps.editor_copilot.artifact_mapper import ArtifactMapper
from app.apps.editor_copilot.schemas import CopilotRequest
from app.apps.editor_copilot.viewmodels import CopilotResponseViewModel
from app.core.goal.models import Goal

logger = logging.getLogger(__name__)

class EditorCopilotApplication:
    """
    Application layer that purely consumes the OS Kernel.
    """
    def __init__(self, platform_scheduler, artifact_repository):
        self.platform_scheduler = platform_scheduler
        self.artifact_repository = artifact_repository

    async def process_intent(self, request: CopilotRequest) -> CopilotResponseViewModel:
        logger.info(f"Editor Copilot processing intent: {request.context.intent}")

        # 1. Map intent to Goal
        goal = Goal(
            goal_id=f"goal_editor_{request.session_id}",
            description=request.context.intent,
            metadata={
                "file_path": request.context.file_path,
                "selected_text": request.context.selected_text
            }
        )

        # 2. Submit Goal to Coordinator via Scheduler
        # (The entire OS lifecycle happens behind this submission)
        await self.platform_scheduler.submit_task(
            capability_name="COORDINATOR",
            version="v1",
            payload={"goal": goal.model_dump()},
            priority=100
        )

        # 3. Await final Artifact (simulated wait)
        # In a real async system, this would be an event subscription.
        # artifact = await self.artifact_repository.wait_for_artifact(goal.goal_id)

        # Simulated artifact
        class DummyArtifact:
            def __init__(self):
                self.content = {"summary": "Refactored to pure function", "diffs": []}

        artifact = DummyArtifact()

        # 4. Map Artifact to ViewModel (ADR-0076)
        return ArtifactMapper.map_to_viewmodel(request.session_id, artifact)
