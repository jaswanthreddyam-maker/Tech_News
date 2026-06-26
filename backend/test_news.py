import asyncio

from app.api.v1.routes.news import list_articles
from app.core.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as db:
        print("Testing list_articles...")
        try:
            resp = await list_articles(category=None, cursor=None, limit=1, db=db)
            print("Success! Got:", resp)
        except Exception as e:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
