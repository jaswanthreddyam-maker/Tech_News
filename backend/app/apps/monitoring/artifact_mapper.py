from app.apps.monitoring.viewmodels import AlertViewModel
from app.core.artifact.models import Artifact


class MonitoringArtifactMapper:
    """
    Translates raw PUBLISHED OS Artifacts into AlertViewModels.
    """
    @staticmethod
    def map_to_viewmodel(artifact: Artifact) -> AlertViewModel:
        content = artifact.content
        return AlertViewModel(
            alert_id=artifact.artifact_id,
            severity=content.get("severity", "WARNING"),
            metric=content.get("metric", "unknown"),
            summary=content.get("summary", "System anomaly detected."),
            source_goal=artifact.metadata.source_goal or "unknown",
            evidence=content.get("evidence", {})
        )
