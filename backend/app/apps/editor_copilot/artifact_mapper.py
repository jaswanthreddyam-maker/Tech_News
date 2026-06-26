from typing import Any

from app.apps.editor_copilot.viewmodels import CopilotResponseViewModel, DiffHunk, FileDiff


class ArtifactMapper:
    """
    Translates raw OS Artifacts into clean UI ViewModels (ADR-0076).
    """
    @staticmethod
    def map_to_viewmodel(session_id: str, artifact: Any) -> CopilotResponseViewModel:
        # Example mapping from an OS Graph Artifact to a UI ViewModel
        diffs = []
        if hasattr(artifact, "content") and "diffs" in artifact.content:
            for d in artifact.content["diffs"]:
                hunks = [DiffHunk(**h) for h in d.get("hunks", [])]
                diffs.append(FileDiff(file_path=d["file_path"], hunks=hunks))

        return CopilotResponseViewModel(
            session_id=session_id,
            status="COMPLETED" if diffs else "FAILED",
            message=artifact.content.get("summary", "No changes proposed."),
            diffs=diffs if diffs else None
        )
