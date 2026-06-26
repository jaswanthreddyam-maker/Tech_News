import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle

async def run():
    async with AsyncSessionLocal() as db:
        # Find articles without key_takeaways
        res = await db.execute(
            select(ProcessedArticle.id)
            .where(ProcessedArticle.key_takeaways.is_(None))
            .where((ProcessedArticle.is_test_data == False) | ProcessedArticle.is_test_data.is_(None))
        )
        article_ids = res.scalars().all()
        print(f"Found {len(article_ids)} articles without key_takeaways")
        
        from celery_app import celery_app
        for art_id in article_ids[:10]:  # Process first 10
            result = celery_app.send_task('generate_structured_summary_task', args=[art_id])
            print(f"  Sent summary task for article {art_id}: {result.id}")
        
        print("Done queuing summary tasks")

asyncio.run(run())
