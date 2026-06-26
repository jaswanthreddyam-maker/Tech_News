import asyncio
import json
from app.core.redis import get_redis_client

async def run():
    redis = get_redis_client()
    cache_key = "editorial:v1:homepage_ranked_ids"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        generated = data.get("generated_at")
        algorithm = data.get("algorithm_version")
        expires = data.get("expires_at")
        ids = data.get("article_ids", [])
        print(f"Redis cache found:")
        print(f"  generated_at: {generated}")
        print(f"  algorithm_version: {algorithm}")
        print(f"  expires_at: {expires}")
        print(f"  article_ids count: {len(ids)}")
        print(f"  first 5 ids: {ids[:5]}")
    else:
        print("No Redis cache found - will be generated on next request")

asyncio.run(run())
