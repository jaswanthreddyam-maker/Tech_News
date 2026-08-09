import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(RawArticle).order_by(RawArticle.id.desc()).limit(3)
        )
        for art in res.scalars():
            print(f"URL: {art.url}")
            print(f"Status: {art.status}")
            print(f"Metadata: {art.article_metadata}")

if __name__ == "__main__":
    asyncio.run(run())
