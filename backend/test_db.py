import asyncio

from app.core.database import AsyncSessionLocal
from app.services.ranking.news_ranking_engine import get_ranked_homepage_articles


async def main():
    async with AsyncSessionLocal() as db:
        print("Testing get_ranked_homepage_articles with commit...")
        try:
            articles = await get_ranked_homepage_articles(db, limit=1)
            await db.commit()
            print(f"Success! Got {len(articles)} articles and committed.")
        except Exception as e:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
