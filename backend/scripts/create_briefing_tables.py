import asyncio
import sys
import os

backend_dir = r"d:\tech_news\backend"
root_dir = r"d:\tech_news"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.core.database import async_engine
from app.models.base import Base
from app.briefing.models import (
    DailyBriefingSubscriber, DailyBriefingEdition, DailyBriefingItem,
    DailyBriefingDelivery, WebhookEvent
)

async def init_tables():
    print("Creating Daily Briefing tables in PostgreSQL...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Daily Briefing tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_tables())
