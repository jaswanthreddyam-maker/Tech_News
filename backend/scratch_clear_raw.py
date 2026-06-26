import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text("TRUNCATE TABLE raw_articles CASCADE;"))
        await db.execute(text("TRUNCATE TABLE processed_articles CASCADE;"))
        await db.execute(text("TRUNCATE TABLE articles CASCADE;"))
        await db.commit()
        print("Truncated raw_articles, processed_articles, articles.")

if __name__ == "__main__":
    asyncio.run(main())
