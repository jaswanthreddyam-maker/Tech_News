import asyncio
from sqlalchemy import update
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle

async def clean_fallbacks():
    async with AsyncSessionLocal() as db:
        res1 = await db.execute(
            update(ArticleReadModel)
            .where(ArticleReadModel.thumbnail_local == '/images/fallback-news.webp')
            .values(thumbnail_local=None, thumbnail_url=None)
        )
        
        res2 = await db.execute(
            update(ProcessedArticle)
            .where(ProcessedArticle.thumbnail_local == '/images/fallback-news.webp')
            .values(thumbnail_local=None, thumbnail_url=None)
        )
        
        await db.commit()
        print(f"Cleaned {res1.rowcount} Read Models and {res2.rowcount} Processed Articles.")

if __name__ == "__main__":
    asyncio.run(clean_fallbacks())
