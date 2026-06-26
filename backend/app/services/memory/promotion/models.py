from typing import Any

from pydantic import BaseModel


class PromotionPolicy(BaseModel):
    """
    Determines how events map to memory promotion workflows.
    """
    event_type: str
    target_memory_types: list[str]
    trigger_condition: dict[str, Any]
    priority: int = 50

# Example definitions (these would live in versioned config or DB)
DEFAULT_PROMOTION_POLICIES = [
    PromotionPolicy(
        event_type="ConversationCompleted",
        target_memory_types=["EPISODIC"],
        trigger_condition={}
    ),
    PromotionPolicy(
        event_type="ArtifactGenerated",
        target_memory_types=["SEMANTIC"],
        trigger_condition={"artifact_type": "ResearchArtifact"}
    ),
    PromotionPolicy(
        event_type="PreferenceChanged",
        target_memory_types=["PREFERENCE"],
        trigger_condition={}
    ),
    PromotionPolicy(
        event_type="WorkflowCompleted",
        target_memory_types=["PROCEDURAL"],
        trigger_condition={"success": True}
    )
]
