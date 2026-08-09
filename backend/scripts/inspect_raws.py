import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel

async def inspect_raws():
    async with AsyncSessionLocal() as db:
        stmt = select(RawArticle)
        res = await db.execute(stmt)
        raws = res.scalars().all()
        print(f"Total RawArticles in DB: {len(raws)}")
        for r in raws:
            print(f"ID: {r.id}, Status: {r.status}, Title: {r.title[:40]}, URL: {r.url[:40]}")

if __name__ == "__main__":
    asyncio.run(inspect_raws())
