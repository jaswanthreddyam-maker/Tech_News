import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

class DomainEventBus:
    """
    Asynchronous dispatcher for domain events.
    Subscribers listen to events and process them completely decoupled from the generator.
    """
    def __init__(self):
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], Awaitable[None]]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], Awaitable[None]]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"DomainEventBus: Registered subscriber for {event_type}")

    async def publish(self, event_type: str, payload: dict[str, Any]):
        logger.info(f"DomainEventBus: Dispatching event {event_type}")
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(payload)
            except Exception as e:
                logger.error(f"DomainEventBus: Subscriber failed processing {event_type}: {e}")
                # We do NOT raise here, as subscribers should not crash the publisher flow.
                # In a robust implementation, this failure might be pushed to a DLQ.
