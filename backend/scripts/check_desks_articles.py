import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle

async def check_articles():
    async with AsyncSessionLocal() as db:
        ids = ['52', '57', '36', '34', '59', '58', '56', '55', '54', '53']
        stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(ids))
        res = await db.execute(stmt)
        read_articles = res.scalars().all()
        print(f"ReadModel found {len(read_articles)} / {len(ids)} articles.")
        for a in read_articles:
            print(f"ID: {a.id}, Title: {a.title[:30]}")

        proc_stmt = select(ProcessedArticle)
        proc_res = await db.execute(proc_stmt)
        procs = proc_res.scalars().all()
        print(f"\nTotal ProcessedArticle in DB: {len(procs)}")
        for p in procs:
            print(f"Proc ID: {p.id}, Category: {p.primary_category_slug or p.category}")

if __name__ == "__main__":
    asyncio.run(check_articles())
