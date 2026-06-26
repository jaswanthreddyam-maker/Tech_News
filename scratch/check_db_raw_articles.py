import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def main():
    async with async_engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT id, title, url, status, scraped_at 
            FROM raw_articles 
            LIMIT 5;
        """))
        rows = res.fetchall()
        print("Raw Articles rows:")
        for r in rows:
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(main())
