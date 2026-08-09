import asyncio
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel
from app.models.projection import HomepageProjection
from datetime import datetime, timedelta, timezone

async def investigate():
    async with AsyncSessionLocal() as session:
        # 1. Total Read Models
        total_res = await session.execute(select(ArticleReadModel.id, ArticleReadModel.published_at))
        all_articles = total_res.all()
        
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        
        recent_count = sum(1 for art in all_articles if art.published_at and art.published_at >= cutoff)
        
        print(f"Total in Read Model: {len(all_articles)}")
        print(f"Total published in last 24h: {recent_count}")
        
        # 2. Check HomepageProjection
        proj_res = await session.execute(
            select(HomepageProjection)
            .order_by(HomepageProjection.created_at.desc())
            .limit(1)
        )
        latest_proj = proj_res.scalars().first()
        if latest_proj and latest_proj.stories_json:
            print(f"HomepageProjection stories count: {len(latest_proj.stories_json)}")
        else:
            print("No HomepageProjection found.")

        # 3. Check Redis cache if possible
        import json
        try:
            from app.core.redis import get_redis_client
            redis = get_redis_client()
            cached = await redis.get("editorial:v1:homepage_ranked_ids")
            if cached:
                cache_data = json.loads(cached)
                print(f"Redis cache ranked_ids count: {len(cache_data.get('article_ids', []))}")
            else:
                print("Redis cache empty or not found.")
        except Exception as e:
            print(f"Redis check failed: {e}")

if __name__ == "__main__":
    asyncio.run(investigate())
