import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel

async def check_read_model():
    target_ids = ["82", "83", "84", "85", "86"]
    async with AsyncSessionLocal() as db:
        stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(target_ids))
        res = await db.execute(stmt)
        articles = res.scalars().all()
        
        for art in articles:
            print(f"[{art.id}] {art.title[:40]}")
            print(f"  thumb_local: {art.thumbnail_local}")
            print(f"  thumb_url: {art.thumbnail_url}")

if __name__ == "__main__":
    asyncio.run(check_read_model())
