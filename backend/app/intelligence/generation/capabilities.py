from typing import Any, Protocol


class AICapability(Protocol):
    """
    Base registry protocol for AI capabilities (RAG, Copilot, Summary, Rewrite).
    Ensures all AI intelligence features operate under a unified deterministic pipeline.
    """
    @property
    def capability_name(self) -> str:
        ...

    @property
    def version(self) -> str:
        ...

    async def execute(self, context: Any, **kwargs) -> Any:
        ...
