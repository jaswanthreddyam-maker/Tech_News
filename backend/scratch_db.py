import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel

async def main():
    async with AsyncSessionLocal() as db:
        raw_count = await db.scalar(select(func.count(RawArticle.id)).where(RawArticle.status == 'filtered'))
        proc_count = await db.scalar(select(func.count(ProcessedArticle.id)))
        read_count = await db.scalar(select(func.count(ArticleReadModel.id)))
        print(f"Filtered RawArticles: {raw_count}")
        print(f"ProcessedArticles: {proc_count}")
        print(f"ArticleReadModels: {read_count}")

if __name__ == "__main__":
    asyncio.run(main())
