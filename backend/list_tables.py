import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def list_tables():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres_secure_pass@127.0.0.1:5433/tech_news_today")
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        print([r[0] for r in res.fetchall()])


asyncio.run(list_tables())
