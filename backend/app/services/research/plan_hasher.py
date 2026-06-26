import hashlib
import json
from typing import Any


class ResearchPlanHasher:
    """
    Generates a deterministic hash for an execution plan to enable aggressive caching.
    """
    @staticmethod
    def generate_hash(
        intent: str, 
        planner_version: str, 
        planner_hash: str, 
        workflow_hash: str, 
        provider_versions: dict[str, str], 
        context_version: str, 
        snapshot_id: int, 
        parameters: dict[str, Any]
    ) -> str:
        payload = {
            "intent": intent,
            "planner_version": planner_version,
            "planner_hash": planner_hash,
            "workflow_hash": workflow_hash,
            "provider_versions": provider_versions,
            "context_version": context_version,
            "snapshot_id": snapshot_id,
            "parameters": parameters
        }

        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
