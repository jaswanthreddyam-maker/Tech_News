import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.events.models import EventOutbox
from app.models.article import ProcessedArticle


async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ProcessedArticle).where(ProcessedArticle.thumbnail_local != None))
        arts = res.scalars().all()
        for art in arts:
            occurred_at = datetime.now(timezone.utc)
            payload = {
                "article_id": str(art.id),
                "thumbnail_local": art.thumbnail_local,
                "thumbnail_url": art.thumbnail_url,
                "thumbnail_hash": getattr(art, "thumbnail_hash", ""),
                "status": getattr(art, "thumbnail_status", "downloaded"),
                "occurred_at": occurred_at.isoformat(),
            }
            db.add(EventOutbox(event_type='ArticleThumbnailUpdated', payload=payload))
        await db.commit()
        print(f'Enqueued {len(arts)} thumbnail update outbox events')

asyncio.run(run())
