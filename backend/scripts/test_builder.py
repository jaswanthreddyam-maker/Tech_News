import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.editorial.homepage_builder import HomepageBuilder

async def test_build_homepage():
    async with AsyncSessionLocal() as session:
        articles = await HomepageBuilder.build_homepage(session)
        print(f"HomepageBuilder returned {len(articles)} articles.")
        for a in articles:
            print(f"- {a.id}: {a.title} ({a.source})")

if __name__ == "__main__":
    asyncio.run(test_build_homepage())
