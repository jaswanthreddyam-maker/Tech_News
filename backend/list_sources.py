import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.source import Source

async def list_sources():
    async with AsyncSessionLocal() as session:
        stmt = select(Source).order_by(Source.id)
        res = await session.execute(stmt)
        sources = res.scalars().all()
        for s in sources:
            print(f"ID: {s.id} | Name: {s.name} | Enabled: {s.enabled} | URL: {s.url}")

if __name__ == "__main__":
    asyncio.run(list_sources())
