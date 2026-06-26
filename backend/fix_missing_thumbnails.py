import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle
from celery_app import download_thumbnail_task


async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ProcessedArticle).where(ProcessedArticle.thumbnail_status == 'pending'))
        arts = res.scalars().all()
        for art in arts:
            download_thumbnail_task.delay(art.id, [])
        print(f'Enqueued download_thumbnail_task for {len(arts)} pending articles')

asyncio.run(run())
