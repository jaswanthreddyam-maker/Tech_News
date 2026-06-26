from abc import ABC, abstractmethod
from typing import Any

from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import ProjectionBatch
from app.core.projection.policy import ProjectionPolicy


class Projector(ABC):
    """
    Abstract base class for pure projectors.
    Projectors consume events and a ProjectionContext to emit a ProjectionBatch.
    """
    @property
    @abstractmethod
    def projection_group(self) -> str:
        """The subsystem group, e.g., 'analytics', 'knowledge'."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the projector."""
        pass

    @property
    @abstractmethod
    def version(self) -> int:
        """The schema version of this projector."""
        pass

    @property
    @abstractmethod
    def supported_events(self) -> list[str]:
        """List of event types this projector consumes."""
        pass

    @property
    def policy(self) -> ProjectionPolicy:
        """The execution policy for this projector."""
        return ProjectionPolicy()

    @property
    def dependencies(self) -> list[str]:
        """Names of other projectors that must run before this one."""
        return []

    @abstractmethod
    async def project(self, event: Any, context: ProjectionContext) -> ProjectionBatch:
        """
        Pure function transforming an event into database mutations.
        """
        pass
