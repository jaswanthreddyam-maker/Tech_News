import asyncio
import json
from sqlalchemy import select, desc
from app.core.database import AsyncSessionLocal
from app.core.events.models import EventOutbox

async def check():
    async with AsyncSessionLocal() as db:
        target_ids = {"86", "82", "83"}
        stmt = (
            select(EventOutbox)
            .where(EventOutbox.event_type == "ArticleThumbnailUpdated")
            .order_by(desc(EventOutbox.id))
            .limit(30)
        )
        res = await db.execute(stmt)
        events = res.scalars().all()
        for e in events:
            aid = str(e.payload.get("article_id", ""))
            if aid in target_ids:
                print(f"Article {aid}: FULL PAYLOAD:")
                print(json.dumps(e.payload, indent=2, default=str))
                print()

asyncio.run(check())
