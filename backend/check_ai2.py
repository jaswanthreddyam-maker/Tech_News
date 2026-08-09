import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.events.models import EventOutbox

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(EventOutbox.payload).where(EventOutbox.event_type.in_(['AI Thumbnail Generated', 'System Event'])).order_by(EventOutbox.id.desc()).limit(10)
        )
        for r in res.scalars():
            print(f"Generated AI: {r}")

if __name__ == "__main__":
    asyncio.run(run())
