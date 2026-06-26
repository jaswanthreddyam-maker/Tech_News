import asyncio
import logging
from typing import Any

from app.core.capability.bus import CapabilityBus

logger = logging.getLogger(__name__)

class ReflectionScheduler:
    """
    Orchestrates reflection capabilities asynchronously off Domain Events.
    ADR-0056: Reflection Is Scheduled.
    """
    def __init__(self, capability_bus: CapabilityBus):
        self.capability_bus = capability_bus
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start(self):
        self._running = True
        asyncio.create_task(self._process_queue())
        logger.info("ReflectionScheduler started.")

    async def stop(self):
        self._running = False
        logger.info("ReflectionScheduler stopped.")

    async def schedule(self, capability_name: str, payload: dict[str, Any], priority: int = 50):
        logger.info(f"ReflectionScheduler: Scheduling {capability_name} at priority {priority}")
        await self._queue.put((priority, capability_name, payload))

    async def _process_queue(self):
        while self._running:
            try:
                # In a real system, use PriorityQueue
                priority, capability_name, payload = await self._queue.get()

                logger.info(f"ReflectionScheduler: Dispatching {capability_name}")
                await self.capability_bus.execute(capability_name, "v1", payload, context={})

                self._queue.task_done()
            except Exception as e:
                logger.error(f"ReflectionScheduler error: {e}")
            await asyncio.sleep(0.1)
