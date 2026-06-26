import asyncio

from sqlalchemy import text

from app.core.database import async_engine


async def check():
    async with async_engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema=public"))
        print([r[0] for r in res.fetchall()])


asyncio.run(check())
