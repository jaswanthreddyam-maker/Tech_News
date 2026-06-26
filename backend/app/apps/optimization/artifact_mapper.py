from app.apps.optimization.viewmodels import OptimizationProposalViewModel
from app.core.artifact.models import Artifact


class OptimizationArtifactMapper:
    """
    Translates PUBLISHED or PENDING_APPROVAL Optimization Artifacts into ViewModels.
    """
    @staticmethod
    def map_to_viewmodel(artifact: Artifact) -> OptimizationProposalViewModel:
        content = artifact.content
        return OptimizationProposalViewModel(
            proposal_id=artifact.artifact_id,
            component=content.get("component", "system"),
            status=artifact.status.value,
            proposed_changes=content.get("proposed_changes", {}),
            expected_impact=content.get("expected_impact", "Unknown"),
            source_goal=artifact.metadata.source_goal or "unknown"
        )
