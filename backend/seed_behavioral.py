import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle
from app.models.behavioral import BehavioralEvent
from app.services.behavioral.session_aggregator import SessionAggregator


async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ProcessedArticle).limit(1))
        article = res.scalar_one_or_none()
        if not article:
            print("No article found")
            return

        # Seed an event
        session_id = str(uuid.uuid4())
        anon_id = str(uuid.uuid4())

        event = BehavioralEvent(
            session_id=session_id,
            anonymous_id=anon_id,
            article_id=article.id,
            event_type="reading_time_update",
            scroll_percent=95,
            reading_time_seconds=article.reading_time * 60 if article.reading_time else 180,
            occurred_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Aggregate
        agg = SessionAggregator(db)
        await agg.aggregate_events([event])
        print(f"Seeded and aggregated session {session_id}")


if __name__ == "__main__":
    asyncio.run(main())
