from dataclasses import dataclass
from typing import Dict, Optional

@dataclass(frozen=True)
class ArchitectureID:
    id: str
    version: int
    owner: str
    deprecated: bool = False

class AIDRegistry:
    _registry: Dict[str, ArchitectureID] = {}

    @classmethod
    def register(cls, aid: ArchitectureID):
        if aid.id in cls._registry:
            raise ValueError(f"DuplicateArchitectureIDError: AID '{aid.id}' is already registered.")
        cls._registry[aid.id] = aid

    @classmethod
    def get(cls, aid_id: str) -> ArchitectureID:
        if aid_id not in cls._registry:
            raise KeyError(f"AID '{aid_id}' is not registered.")
        return cls._registry[aid_id]

    @classmethod
    def all(cls) -> Dict[str, ArchitectureID]:
        return cls._registry.copy()

# ---------------------------------------------------------
# Reserved Namespaces
# ---------------------------------------------------------

class Constitution:
    PRINCIPLES = ArchitectureID(id="constitution.principles", version=1, owner="architecture")
    INVARIANTS = ArchitectureID(id="constitution.invariants", version=1, owner="architecture")
    GOVERNANCE = ArchitectureID(id="constitution.governance", version=1, owner="architecture")
    NON_GOALS = ArchitectureID(id="constitution.non_goals", version=1, owner="architecture")
    BOUNDED_CONTEXTS = ArchitectureID(id="constitution.bounded_contexts", version=1, owner="architecture")
    QUALITY_ATTRIBUTES = ArchitectureID(id="constitution.quality_attributes", version=1, owner="architecture")
    ADR_LIFECYCLE = ArchitectureID(id="constitution.adr_lifecycle", version=1, owner="architecture")

# Auto-register reserved namespaces
for namespace in [Constitution]:
    for attr_name in dir(namespace):
        if not attr_name.startswith("__"):
            aid_obj = getattr(namespace, attr_name)
            if isinstance(aid_obj, ArchitectureID):
                AIDRegistry.register(aid_obj)
