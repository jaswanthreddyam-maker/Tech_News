import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.projection import CategoryDeskProjection

async def check_desks():
    async with AsyncSessionLocal() as db:
        stmt = select(CategoryDeskProjection)
        res = await db.execute(stmt)
        projections = res.scalars().all()
        print(f"Total CategoryDeskProjections: {len(projections)}")
        for p in projections:
            print(f"Slug: {p.category_slug}, Articles: {p.article_ids}")

if __name__ == "__main__":
    asyncio.run(check_desks())
