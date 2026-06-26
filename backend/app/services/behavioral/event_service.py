import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavioral import BehavioralEvent
from app.schemas.behavioral import BehavioralBatchRequest
from app.services.behavioral.session_aggregator import SessionAggregator

logger = logging.getLogger(__name__)


class BehavioralEventService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.aggregator = SessionAggregator(db)

    async def process_batch(self, request: BehavioralBatchRequest, user_id: int | None) -> dict:
        """
        Process a batch of behavioral events idempotently.
        """
        processed_count = 0
        deduplicated_count = 0
        failed_count = 0

        # 1. Extract event IDs from the batch to check for existing events
        incoming_event_ids = [event.event_id for event in request.events]

        if not incoming_event_ids:
            return {"processed": 0, "deduplicated": 0, "failed": 0}

        # 2. Query DB for existing event IDs
        result = await self.db.execute(
            select(BehavioralEvent.event_id).where(BehavioralEvent.event_id.in_(incoming_event_ids))
        )
        existing_event_ids = set(result.scalars().all())

        new_events = []
        for payload in request.events:
            if payload.event_id in existing_event_ids:
                deduplicated_count += 1
                continue

            try:
                event = BehavioralEvent(
                    event_id=payload.event_id,
                    user_id=user_id,
                    anonymous_id=request.anonymous_id,
                    article_id=payload.article_id,
                    session_id=payload.session_id,
                    event_type=payload.event_type,
                    event_version=payload.event_version,
                    content_version=payload.content_version,
                    scroll_percent=payload.scroll_percent,
                    reading_time_seconds=payload.reading_time_seconds,
                    occurred_at=payload.occurred_at,
                    device_type=payload.device_type,
                    referrer=payload.referrer,
                    metadata_payload=payload.metadata_payload,
                )
                self.db.add(event)
                new_events.append(event)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process behavioral event {payload.event_id}: {e}")
                failed_count += 1

        from sqlalchemy.exc import IntegrityError
        # 3. Flush new events
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(f"IntegrityError during batch commit, likely concurrent deduplication: {e}")
            return {"processed": 0, "deduplicated": len(new_events), "failed": 0}
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to commit behavioral events batch: {e}")
            raise

        # 4. Synchronously aggregate session data
        if new_events:
            await self.aggregator.aggregate_events(new_events)

        return {"processed": processed_count, "deduplicated": deduplicated_count, "failed": failed_count}
