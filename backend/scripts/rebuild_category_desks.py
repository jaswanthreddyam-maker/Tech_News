import asyncio
from app.core.database import AsyncSessionLocal
from app.editorial.homepage_builder import HomepageBuilder

async def rebuild():
    async with AsyncSessionLocal() as db:
        print("Rebuilding category desk projections...")
        desks = await HomepageBuilder.build_and_persist_category_desks(db)
        print(f"Rebuilt {len(desks)} category desks!")
        for d in desks:
            print(f"Category: {d.category_slug}, Article Count: {len(d.article_ids)}")

if __name__ == "__main__":
    asyncio.run(rebuild())
