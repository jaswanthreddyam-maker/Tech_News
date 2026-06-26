import asyncio
import hashlib

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.events.models import EventOutbox
from app.models.article import ProcessedArticle


async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ProcessedArticle))
        arts = res.scalars().all()
        for art in arts:
            hash_val = hashlib.sha256(art.content.encode('utf-8')).hexdigest() if art.content else ''
            db.add(EventOutbox(event_type='ArticlePublished', payload={
                'id': str(art.id),
                'url': art.slug,
                'title': art.title,
                'content': art.content,
                'hash': hash_val,
                'source': art.source_name,
                'thumbnail_url': getattr(art, 'thumbnail_url', None),
                'thumbnail_local': getattr(art, 'thumbnail_local', None),
                'published_at': art.published_at.isoformat() if art.published_at else None,
                'is_test_data': getattr(art, 'is_test_data', False)
            }))
        await db.commit()
        print(f'Enqueued {len(arts)} outbox events')

asyncio.run(run())
