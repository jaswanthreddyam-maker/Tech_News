import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.projection import HomepageProjection

async def main():
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(HomepageProjection).order_by(HomepageProjection.created_at.desc()))
        projs = res.scalars().all()
        print(f"Total Projections in Container DB: {len(projs)}")
        for p in projs:
            print(f"  ID: {p.id} | Ver: {p.projection_version} | CreatedAt: {p.created_at}")

if __name__ == "__main__":
    asyncio.run(main())
