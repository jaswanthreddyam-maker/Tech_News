import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, Category, ArticleReadModel

async def check_cat():
    async with AsyncSessionLocal() as db:
        cats = (await db.execute(select(Category))).scalars().all()
        print(f"Categories count: {len(cats)}")
        for c in cats:
            print(f"  Category ID: {c.id}, Name: {c.name}, Slug: {c.slug}")

        procs = (await db.execute(select(ProcessedArticle))).scalars().all()
        print(f"\nProcessedArticle count: {len(procs)}")
        for p in procs:
            print(f"  ID: {p.id}, Title: {p.title[:30]}, category_id: {p.category_id}")

        reads = (await db.execute(select(ArticleReadModel))).scalars().all()
        print(f"\nArticleReadModel count: {len(reads)}")
        for r in reads:
            print(f"  ID: {r.id}, Title: {r.title[:30]}, Category: {r.category}")

if __name__ == "__main__":
    asyncio.run(check_cat())
