import logging
from typing import Any

from app.core.capability.models import CapabilityContract
from app.core.capability.registry import CapabilityInterface
from app.services.memory.retrieval.models import DEFAULT_RETRIEVAL_POLICIES, RetrievalRequest

logger = logging.getLogger(__name__)

class MemoryRetrievalCapability(CapabilityInterface):
    """
    Plugs into the CapabilityBus.
    Provides intent-aware memory fetching.
    """
    def __init__(self, memory_index: Any, vector_adapter: Any):
        self.memory_index = memory_index
        self.vector_adapter = vector_adapter

    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="MEMORY_RETRIEVAL",
            version="v1",
            input_schema=RetrievalRequest.model_json_schema(),
            output_schema={"type": "object"}, # List of memories
            required_policies=["PRIVACY_POLICY", "BUDGET_POLICY"]
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        req = RetrievalRequest(**payload)
        logger.info(f"MemoryRetrievalCapability: Fetching memory for intent {req.intent}")

        # Determine policies
        policy = next((p for p in DEFAULT_RETRIEVAL_POLICIES if p.intent == req.intent), None)
        types_to_fetch = req.memory_types if req.memory_types else (policy.target_memory_types if policy else ["EPISODIC"])

        logger.info(f"MemoryRetrievalCapability: Extracting types {types_to_fetch} up to budget {req.budget}")

        # 1. Search Vector DB via Adapter
        # 2. Join with MemoryIndex
        # 3. Filter by required_confidence and max_tokens_budget
        # 4. Return results

        return {"memories": [], "metadata": {"types_fetched": types_to_fetch}}
