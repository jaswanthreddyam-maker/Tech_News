import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.projection import HomepageProjection
from app.models.article import ArticleReadModel
import json
from app.core.redis import get_redis_client

async def run():
    async with AsyncSessionLocal() as db:
        stmt = select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1)
        res = await db.execute(stmt)
        proj = res.scalars().first()
        if proj:
            stories = json.loads(proj.stories_json) if isinstance(proj.stories_json, str) else proj.stories_json
            print(f"Latest Projection v{proj.projection_version}: {len(stories)} stories")
            for s in stories:
                print(f"  ID {s.get('id')} - {s.get('title', '')[:30]}...")
        else:
            print("No projections found!")
            
        r = get_redis_client()
        cached = await r.get("editorial:v1:homepage_ranked_ids")
        print(f"Redis cached: {cached}")
        
        res = await db.execute(select(ArticleReadModel.id).limit(10))
        arm_ids = res.scalars().all()
        print(f"ArticleReadModel has {len(arm_ids)} random articles: {arm_ids}")
        
        res = await db.execute(select(ArticleReadModel).where(ArticleReadModel.id.in_(["86", "82", "83"])))
        found = res.scalars().all()
        print(f"ArticleReadModel target articles: {[a.id for a in found]}")

if __name__ == "__main__":
    asyncio.run(run())
