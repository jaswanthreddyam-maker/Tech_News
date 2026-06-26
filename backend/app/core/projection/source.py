from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventEnvelope


class ProjectionSource(ABC):
    @abstractmethod
    async def stream(self, **kwargs) -> AsyncIterator[Any]:
        yield

class EventEnvelopeSource(ProjectionSource):
    """
    Streams events from the EventEnvelope table.
    Can be configured for partial replays.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def stream(self, **kwargs) -> AsyncIterator[EventEnvelope]:
        start_time = kwargs.get("start_time")
        event_ids = kwargs.get("event_ids")
        categories = kwargs.get("categories")
        stmt = select(EventEnvelope).order_by(EventEnvelope.id)

        if start_time:
            stmt = stmt.where(EventEnvelope.occurred_at >= start_time)
        if event_ids:
            stmt = stmt.where(EventEnvelope.id.in_(event_ids))
        if categories:
            stmt = stmt.where(EventEnvelope.category.in_(categories))

        # We execute and iterate
        # In a very large DB, we should use server-side cursors (yield_per)
        result = await self.session.stream(stmt.execution_options(yield_per=1000))
        async for partition in result.partitions():
            for row in partition:
                yield row[0]
