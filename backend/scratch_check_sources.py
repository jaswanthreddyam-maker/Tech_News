import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from app.models.article import RawArticle, ProcessedArticle
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source))
        for s in res.scalars().all():
            print(s.id, s.name, s.url, s.enabled)

if __name__ == "__main__":
    asyncio.run(main())
