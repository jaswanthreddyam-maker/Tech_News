import asyncio
from app.core.database import async_engine
from sqlalchemy import text

async def main():
    async with async_engine.connect() as conn:
        res = await conn.execute(text("SELECT id, name, url FROM sources"))
        for row in res.fetchall():
            print(f"ID: {row[0]}, Name: {row[1]}, URL: {row[2]}")

if __name__ == '__main__':
    asyncio.run(main())
