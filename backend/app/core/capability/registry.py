import logging
from typing import Any

from app.core.capability.models import CapabilityContract

logger = logging.getLogger(__name__)

class CapabilityInterface:
    @property
    def contract(self) -> CapabilityContract:
        raise NotImplementedError()

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        raise NotImplementedError()

    async def compensate(self, payload: dict[str, Any], context: Any) -> None:
        """
        Saga pattern (ADR-0064). Reverts side effects if downstream capabilities fail.
        By default, does nothing for read-only capabilities.
        """
        pass

class CapabilityRegistry:
    """
    Universal registry for all capabilities.
    """
    def __init__(self):
        self._capabilities: dict[str, dict[str, CapabilityInterface]] = {}

    def register(self, capability: CapabilityInterface):
        name = capability.contract.name
        version = capability.contract.version
        if name not in self._capabilities:
            self._capabilities[name] = {}
        self._capabilities[name][version] = capability
        logger.info(f"Registered Capability: {name} v{version}")

    def get_capability(self, name: str, version: str = "v1") -> CapabilityInterface:
        if name not in self._capabilities or version not in self._capabilities[name]:
            raise ValueError(f"Capability {name} v{version} not found.")
        return self._capabilities[name][version]
