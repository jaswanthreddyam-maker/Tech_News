from abc import ABC, abstractmethod
from typing import Any

class CapabilityProvider(ABC):
    """
    The base interface for all Discovery capabilities.
    Examples: ASTProvider, MarkdownProvider, OpenAPIProvider, PrometheusProvider.
    """
    @property
    @abstractmethod
    def capability_type(self) -> str:
        ...

    @abstractmethod
    def discover(self) -> Any:
        """Runs the discovery engine for this specific capability."""
        ...

    @abstractmethod
    def version(self) -> str:
        ...
