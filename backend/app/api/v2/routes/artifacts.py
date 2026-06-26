from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.artifact.repository import ArtifactRepository

router = APIRouter(prefix="/artifacts", tags=["Enterprise Gateway"])

class ViewNegotiator:
    """
    Translates PUBLISHED Artifacts into specific ViewModels (ADR-0079).
    """
    @staticmethod
    def negotiate(artifact: Any, view: str) -> dict[str, Any]:
        content = artifact.content
        if view == "summary":
            return {"id": artifact.artifact_id, "summary": content.get("summary", "No summary")}
        elif view == "admin":
            return {"id": artifact.artifact_id, "metrics": content.get("metrics", {}), "source_goal": artifact.metadata.source_goal}
        else: # full
            return {"id": artifact.artifact_id, "content": content}

@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: str, 
    view: str = Query("full", description="View representation (summary, full, admin)"),
    repo: ArtifactRepository = Depends()
):
    """
    Strictly returns PUBLISHED artifacts.
    Internal kernel states are hidden.
    """
    artifact = await repo.get_published(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found or not yet published.")

    return ViewNegotiator.negotiate(artifact, view)
