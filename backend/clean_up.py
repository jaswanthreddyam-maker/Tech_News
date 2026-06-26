import asyncio

from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle


async def run():
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ProcessedArticle).where(ProcessedArticle.title.like('%[%]%')))
        await session.commit()
    print('Cleaned up')

if __name__ == '__main__':
    asyncio.run(run())
