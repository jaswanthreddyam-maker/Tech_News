import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel

async def check_scores():
    async with AsyncSessionLocal() as db:
        reads = (await db.execute(select(ArticleReadModel))).scalars().all()
        for r in reads:
            print(f"ID: {r.id}, Title: {r.title[:30]}, final_score: {r.final_score}, freshness_score: {r.freshness_score}")

if __name__ == "__main__":
    asyncio.run(check_scores())
