import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from app.core.database import AsyncSessionLocal
from app.services.ingestion.pipeline import crawl_single_source_pipeline
from app.models.source import Source
from sqlalchemy import select

async def test_sources():
    sources_to_test = [15, 16, 13, 14]  # TechCrunch, Verge, NVIDIA, DeepMind
    
    async with AsyncSessionLocal() as session:
        # Temporarily enable them for the force crawl if needed, but force_crawl checks if enabled.
        # So we must enable them first.
        stmt = select(Source).where(Source.id.in_(sources_to_test))
        res = await session.execute(stmt)
        sources = res.scalars().all()
        for s in sources:
            s.enabled = True
        await session.commit()

        for sid in sources_to_test:
            print(f"\n--- Testing Source ID {sid} ---")
            metrics = await crawl_single_source_pipeline(session, sid)
            print(f"Metrics for {sid}: {metrics}")

if __name__ == "__main__":
    asyncio.run(test_sources())
