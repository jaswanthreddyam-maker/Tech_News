import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import text

from app.core.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        await session.execute(text("TRUNCATE TABLE articles CASCADE;"))
        await session.execute(text("TRUNCATE TABLE projection_failures CASCADE;"))
        await session.execute(text("TRUNCATE TABLE projection_checkpoints CASCADE;"))
        await session.commit()

asyncio.run(main())
