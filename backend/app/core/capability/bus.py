import logging
from typing import Any

from app.core.capability.registry import CapabilityRegistry

logger = logging.getLogger(__name__)

class CapabilityBus:
    """
    Central routing mechanism for all capability execution.
    Enforces policies before dispatching to the capability interface.
    """
    def __init__(self, registry: CapabilityRegistry, policy_engine: Any = None):
        self.registry = registry
        self.policy_engine = policy_engine

    async def execute(self, capability_name: str, version: str, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        logger.info(f"CapabilityBus: Received request for {capability_name} v{version}")

        capability = self.registry.get_capability(capability_name, version)

        # Policy Enforcement (ADR-0044)
        if self.policy_engine:
            decision = await self.policy_engine.execute(capability.contract.required_policies, context)
            if not decision.allowed:
                raise PermissionError(f"Policy violation: {decision.reason}")

        # Schema Validation (ADR-0043)
        # Assuming capability input schema validation happens here

        # Execute
        result = await capability.execute(payload, context)

        # Schema Validation for output
        return result
