import asyncio
from sqlalchemy import select, desc
from app.core.database import AsyncSessionLocal
from app.core.events.models import EventOutbox

async def check():
    async with AsyncSessionLocal() as db:
        stmt = (
            select(EventOutbox)
            .where(EventOutbox.event_type == "ArticleThumbnailUpdated")
            .order_by(desc(EventOutbox.id))
            .limit(15)
        )
        res = await db.execute(stmt)
        events = res.scalars().all()
        print(f"Found {len(events)} ArticleThumbnailUpdated events")
        for e in events:
            aid = e.payload.get("article_id", "?")
            tl = e.payload.get("thumbnail_local", "?")
            print(f"  EventOutbox ID={e.id}  status={e.status}  article_id={aid}  thumbnail_local={tl}")

asyncio.run(check())
