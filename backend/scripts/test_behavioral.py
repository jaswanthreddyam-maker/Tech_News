import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from datetime import datetime, timezone

import pytest

from app.core.database import AsyncSessionLocal
from app.schemas.behavioral import BehavioralBatchRequest, BehavioralEventPayload
from app.services.behavioral.event_service import BehavioralEventService


@pytest.mark.asyncio
async def test_behavioral():
    async with AsyncSessionLocal() as db:
        service = BehavioralEventService(db)

        session_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())

        req = BehavioralBatchRequest(
            events=[
                BehavioralEventPayload(
                    event_id=event_id,
                    article_id=1,
                    session_id=session_id,
                    event_type="article_opened",
                    event_version="v1",
                    content_version="v1",
                    scroll_percent=0,
                    reading_time_seconds=0,
                    occurred_at=datetime.now(timezone.utc),
                    device_type="desktop",
                )
            ],
            anonymous_id="test_anon",
        )

        print("First insert:")
        res1 = await service.process_batch(req, user_id=None)
        print(res1)

        print("Second insert (idempotency test):")
        res2 = await service.process_batch(req, user_id=None)
        print(res2)


if __name__ == "__main__":
    asyncio.run(test_behavioral())
