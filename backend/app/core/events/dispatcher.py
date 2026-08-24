import asyncio
import logging
from typing import Any

from app.core.events.bus import DomainEventBus

logger = logging.getLogger(__name__)

class BackgroundDispatcher:
    """
    DEPRECATED — Do not use for new code.

    The canonical outbox dispatcher is the Celery periodic task
    ``process_event_outbox_task`` in ``app/tasks/distribution_tasks.py``,
    which implements:
      - CTE + FOR UPDATE SKIP LOCKED lease acquisition
      - Per-handler checkpoint idempotency (OutboxDispatchCheckpoint)
      - Per-event savepoint isolation
      - Dead letter routing on max retries
      - Expired lease reclamation for crashed worker recovery

    This class is retained only for reference. The only external reference
    is a comment in ``app/services/replay_service.py`` (line 85).

    See ADR-0041: Transactional Outbox.
    """
    def __init__(self, event_bus: DomainEventBus, session_maker: Any):
        self.event_bus = event_bus
        self.session_maker = session_maker
        self._running = False

    async def start(self):
        self._running = True
        asyncio.create_task(self._poll_loop())
        logger.info("BackgroundDispatcher started.")

    async def stop(self):
        self._running = False
        logger.info("BackgroundDispatcher stopped.")

    async def _poll_loop(self):
        while self._running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error(f"BackgroundDispatcher poll error: {e}")
            await asyncio.sleep(5) # Poll interval

    async def _process_batch(self):
        # 1. Fetch CREATED or RETRYING outbox events.
        # 2. Acquire lease (UPDATE ... SET status=LEASED, lease_id=uuid, lease_expires_at=now+1m WHERE status IN ('CREATED', 'RETRYING')).
        # 3. For each leased event:
        #      status = DISPATCHING
        #      try: 
        #          await self.event_bus.publish(event.event_type, event.payload)
        #          status = DELIVERED
        #      except:
        #          retry_count++
        #          status = FAILED -> RETRYING or DEAD_LETTER (if max_retries)
        # 4. Commit ACKs.
        pass
