from app.distribution.capabilities.base import DistributionCapability


class DistributionCapabilityRegistry:
    def __init__(self):
        self._capabilities: dict[str, DistributionCapability] = {}

    def register(self, capability: DistributionCapability):
        self._capabilities[capability.id] = capability

    def get(self, capability_id: str) -> DistributionCapability:
        cap = self._capabilities.get(capability_id)
        if not cap:
            raise KeyError(f"Capability {capability_id} not found")
        return cap

    def active(self) -> list[DistributionCapability]:
        """Returns all enabled capabilities sorted by priority."""
        active_caps = [c for c in self._capabilities.values() if c.enabled]
        return sorted(active_caps, key=lambda c: c.priority)

# Global singleton registry
registry = DistributionCapabilityRegistry()
