import asyncio
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        stmt = select(RawArticle.id, RawArticle.title, RawArticle.url, RawArticle.status, RawArticle.error_log).limit(10)
        res = await db.execute(stmt)
        print("--- RAW ARTICLES ---")
        for row in res.all():
            print(f"ID={row.id} | Title={row.title} | Status={row.status} | Err={row.error_log}")

if __name__ == "__main__":
    asyncio.run(main())
