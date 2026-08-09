import asyncio, os, sys
sys.path.insert(0, os.getcwd())
from app.core.database import AsyncSessionLocal
from app.editorial.homepage_builder import HomepageBuilder
async def main():
    async with AsyncSessionLocal() as db:
        await HomepageBuilder.build_and_persist_category_desks(db)
        print('DONE')
asyncio.run(main())
