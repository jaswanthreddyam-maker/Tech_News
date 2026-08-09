import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(
                ProcessedArticle.title,
                ProcessedArticle.thumbnail_status,
                ProcessedArticle.thumbnail_generation_reason,
                ProcessedArticle.candidate_count,
                ProcessedArticle.thumbnail_type,
                ProcessedArticle.thumbnail_local
            ).order_by(ProcessedArticle.id.desc()).limit(10)
        )
        for r in res.all():
            print(f"Title: {r[0][:30]} | Status: {r[1]} | Reason: {r[2]} | Cand: {r[3]} | Type: {r[4]} | Local: {r[5]}")

if __name__ == "__main__":
    asyncio.run(run())
