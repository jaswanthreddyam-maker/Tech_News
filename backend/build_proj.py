import asyncio
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from app.editorial.homepage_builder import HomepageBuilder

async def run():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        articles = await HomepageBuilder.build_homepage(db)
        print('Built articles:', len(articles))
        if articles:
            stories_json = json.dumps([{
                'id': a.id,
                'title': a.title,
                'category': a.category,
                'source': a.source,
                'slug': a.slug,
                'published_at': a.published_at.isoformat() if a.published_at else None,
                'thumbnail_url': a.thumbnail_url
            } for a in articles])
            
            await db.execute(text(
                "INSERT INTO homepage_projections (id, projection_version, created_at, stories_json) "
                "VALUES (:id, :ver, :created_at, CAST(:stories_json AS jsonb))"
            ), {
                'id': str(uuid.uuid4()),
                'ver': 1,
                'created_at': datetime.utcnow(),
                'stories_json': stories_json
            })
            await db.commit()
            print('Saved projection!')

asyncio.run(run())
