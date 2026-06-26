import logging

from app.core.artifact.models import Artifact, ArtifactStatus

logger = logging.getLogger(__name__)

class ArtifactRepository:
    """
    Repository for AI OS Artifacts. 
    Enforces ADR-0077 by only returning PUBLISHED artifacts to consumers.
    """
    def __init__(self, session_maker):
        self.session_maker = session_maker
        # In-memory storage for demonstration
        self._artifacts = {}

    async def save(self, artifact: Artifact) -> None:
        self._artifacts[artifact.artifact_id] = artifact
        logger.info(f"Artifact {artifact.artifact_id} saved with status {artifact.status.value}")

    async def get_published(self, artifact_id: str) -> Artifact | None:
        """
        Applications should only call this method. (ADR-0077)
        """
        artifact = self._artifacts.get(artifact_id)
        if artifact and artifact.status == ArtifactStatus.PUBLISHED:
            return artifact
        return None

    async def get_all_published_by_goal(self, goal_id: str) -> list[Artifact]:
        return [
            a for a in self._artifacts.values() 
            if a.status == ArtifactStatus.PUBLISHED 
            and a.metadata.source_goal == goal_id
        ]

    async def get_internal(self, artifact_id: str) -> Artifact | None:
        """
        Kernel-internal method for reading non-published artifacts.
        Applications MUST NOT call this.
        """
        return self._artifacts.get(artifact_id)
