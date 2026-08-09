import asyncio
from app.core.database import AsyncSessionLocal
from app.editorial.homepage_builder import HomepageBuilder
import urllib.request
import json

async def rebuild():
    async with AsyncSessionLocal() as db:
        print("Rebuilding HomepageProjection and Redis ranking cache...")
        articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
        print(f"Rebuilt homepage ranking! Articles count: {len(articles)}")
        print(f"Article IDs: {[a.id for a in articles]}")

    req = urllib.request.urlopen("http://localhost:8000/api/v1/news")
    data = json.loads(req.read().decode('utf-8'))
    articles = data if isinstance(data, list) else data.get("data", [])
    print(f"\nLive Trending API now returns: {len(articles)} articles!")

if __name__ == "__main__":
    asyncio.run(rebuild())
