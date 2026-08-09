import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle

async def check():
    target_ids = [82, 83, 84, 85, 86]
    async with AsyncSessionLocal() as db:
        stmt = select(ProcessedArticle).where(ProcessedArticle.id.in_(target_ids))
        res = await db.execute(stmt)
        articles = res.scalars().all()
        for art in articles:
            print(f"[{art.id}] {art.title[:40]}")
            print(f"  thumb_local: {art.thumbnail_local}")
            print(f"  thumb_url: {art.thumbnail_url}")
            print(f"  thumb_type: {art.thumbnail_type}")
            print(f"  candidate_count: {art.candidate_count}")
            print(f"  winner_pass: {art.winner_pass}")
            print(f"  source: {art.thumbnail_source}")

if __name__ == "__main__":
    asyncio.run(check())
