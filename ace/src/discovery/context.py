from typing import Dict, Any, List
from ace.src.contracts.capability import CapabilityProvider

class CapabilityRegistry:
    def __init__(self):
        self._capabilities: Dict[str, CapabilityProvider] = {}

    def register(self, capability: CapabilityProvider):
        self._capabilities[capability.capability_type] = capability

    def get(self, name: str) -> CapabilityProvider:
        if name not in self._capabilities:
            raise KeyError(f"Capability '{name}' is not registered.")
        return self._capabilities[name]

    def has(self, name: str) -> bool:
        return name in self._capabilities

class RepositoryContext:
    """
    The aggregator of all Discovery capabilities.
    Used by the Knowledge Engine to build the ArchitectureModel.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.capabilities = CapabilityRegistry()
