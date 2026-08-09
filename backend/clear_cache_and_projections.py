import sys
import os

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.grqjnmzteryrxfossice:Jaswanthreddy123456@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

import asyncio
from sqlalchemy import delete
from app.core.database import AsyncSessionLocal
from app.models.projection import HomepageProjection
from app.core.redis import get_redis_client
from app.editorial.homepage_builder import HomepageBuilder

async def main():
  async with AsyncSessionLocal() as db:
    print("1. Deleting stale HomepageProjection records...")
    await db.execute(delete(HomepageProjection))
    await db.commit()

    print("2. Invalidating Redis cache keys...")
    try:
      redis = get_redis_client()
      if redis:
        await redis.delete("editorial:v1:homepage_ranked_ids")
        await redis.delete("homepage:v1:curated_projection")
        await redis.delete("ranking_engine_metrics")
        print("Redis cache keys cleared!")
    except Exception as e:
      print(f"Redis clear note: {e}")

    print("3. Rebuilding fresh HomepageProjection with thumbnails...")
    await HomepageBuilder.build_homepage(db)
    print("Fresh homepage build complete!")

if __name__ == "__main__":
  asyncio.run(main())
