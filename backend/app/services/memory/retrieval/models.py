from typing import Any

from pydantic import BaseModel


class RetrievalPolicy(BaseModel):
    """
    Dictates what memory types are fetched for specific intents.
    """
    intent: str
    target_memory_types: list[str]
    max_tokens_budget: int
    required_confidence: float = 0.7

# Example definitions
DEFAULT_RETRIEVAL_POLICIES = [
    RetrievalPolicy(
        intent="RESEARCH",
        target_memory_types=["SEMANTIC", "PROCEDURAL"],
        max_tokens_budget=5000
    ),
    RetrievalPolicy(
        intent="CONVERSATION",
        target_memory_types=["WORKING", "EPISODIC"],
        max_tokens_budget=2000
    ),
    RetrievalPolicy(
        intent="COMPARISON",
        target_memory_types=["SEMANTIC"],
        max_tokens_budget=4000
    )
]

class RetrievalRequest(BaseModel):
    intent: str
    memory_types: list[str] | None = None
    limits: int = 10
    budget: dict[str, Any]
    snapshot_id: int
