import sys
import os

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.grqjnmzteryrxfossice:Jaswanthreddy123456@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

import asyncio
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, ArticleReadModel
from app.apps.tnt.projectors import ArticleProjector
from app.editorial.homepage_builder import HomepageBuilder
from app.core.redis import get_redis_client

async def main():
  async with AsyncSessionLocal() as session:
    from sqlalchemy.orm import selectinload
    stmt = select(ProcessedArticle).options(selectinload(ProcessedArticle.category)).where(ProcessedArticle.published_status == 'published')
    res = await session.execute(stmt)
    articles = res.scalars().all()
    print(f"Found {len(articles)} published ProcessedArticles to project...")

    projector = ArticleProjector()
    for pa in articles:
      artifact_id = str(pa.id)
      cat_name = pa.category.name if pa.category else "Technology"
      
      article_data = {
        "id": artifact_id,
        "url": pa.slug,
        "canonical_url": pa.slug,
        "title": pa.title,
        "subtitle": "",
        "author": "TNT Editorial",
        "published_at": pa.published_at.isoformat() if pa.published_at else None,
        "updated_at": pa.created_at.isoformat() if pa.created_at else None,
        "language": "en",
        "summary": pa.summary,
        "content": pa.content,
        "word_count": len(pa.content.split()) if pa.content else 0,
        "reading_time": pa.reading_time,
        "images": [],
        "tags": [],
        "source": pa.source_name or pa.source or "Web",
        "license": "Copyright",
        "hash": f"hash_{pa.id}",
        "thumbnail_url": pa.thumbnail_url,
        "thumbnail_local": pa.thumbnail_local,
        "is_test_data": pa.is_test_data,
        "freshness_score": pa.freshness_score or 100.0,
        "engagement_score": pa.engagement_score or 100.0,
        "final_score": pa.final_score or 100.0,
        "category": cat_name,
        "published_status": "published"
      }
      await projector.project(artifact_id, article_data, session)

    await session.commit()
    print("Projected all articles to ArticleReadModel successfully!")

    # Direct SQL update safeguard to ensure thumbnail_url is never null in ArticleReadModel
    for pa in articles:
      if pa.thumbnail_url:
        await session.execute(
          update(ArticleReadModel)
          .where(ArticleReadModel.id == str(pa.id))
          .values(thumbnail_url=pa.thumbnail_url, thumbnail_local=pa.thumbnail_local)
        )

    await session.commit()
    print("Safeguard SQL update complete for thumbnail URLs!")

    # Clear Redis cache
    redis = get_redis_client()
    if redis:
      await redis.delete("editorial:v1:homepage_ranked_ids")
      await redis.delete("homepage:v1:curated_projection")

    # Rebuild homepage
    await HomepageBuilder.build_homepage(session)
    print("Homepage rebuilt with read model thumbnails!")

if __name__ == "__main__":
  asyncio.run(main())
