import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle
from celery_app import process_raw_article_task


async def main():
    print("Manual Trigger: retroactively queueing all fetched raw articles for processing...")
    async with AsyncSessionLocal() as db:
        stmt = select(RawArticle).where(RawArticle.status == "fetched")
        res = await db.execute(stmt)
        articles = res.scalars().all()

        if not articles:
            print("No raw articles found with status 'fetched'.")
            return

        print(f"Queueing {len(articles)} raw articles to Celery worker...")
        for art in articles:
            process_raw_article_task.delay(art.id)
            print(f" - Enqueued RawArticle ID {art.id}: {art.title}")
        print("All fetched articles successfully enqueued!")


if __name__ == "__main__":
    asyncio.run(main())
