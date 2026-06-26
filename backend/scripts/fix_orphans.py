import asyncio

from sqlalchemy import update

from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel


async def fix():
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ArticleReadModel)
            .where(ArticleReadModel.thumbnail_local == '/api/v1/uploads/thumbnails/fallback-news.webp')
            .values(thumbnail_local='/images/fallback-news.webp')
        )
        await session.commit()

if __name__ == "__main__":
    asyncio.run(fix())
