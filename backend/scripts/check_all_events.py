import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.events.models import EventOutbox

async def check():
    async with AsyncSessionLocal() as db:
        target_ids = {"86", "82", "83"}
        stmt = select(EventOutbox).order_by(EventOutbox.id)
        res = await db.execute(stmt)
        events = res.scalars().all()
        
        for e in events:
            aid = str(e.payload.get("article_id") or e.payload.get("id", ""))
            if aid in target_ids:
                tl = e.payload.get("thumbnail_local", "N/A")
                print(f"  ID={e.id:4d}  type={e.event_type:45s}  status={e.status:12s}  art={aid}")

asyncio.run(check())
