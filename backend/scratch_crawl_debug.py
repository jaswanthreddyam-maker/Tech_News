import asyncio
import logging
from app.core.database import AsyncSessionLocal
from app.services.ingestion.pipeline import crawl_single_source_pipeline

# Enable debug logging so we can see all logger statements
logging.basicConfig(level=logging.INFO)
logging.getLogger("tech_news").setLevel(logging.DEBUG)

async def main():
    async with AsyncSessionLocal() as db:
        print("Running manual crawl with debug logs...")
        metrics = await crawl_single_source_pipeline(db, 4)
        print(f"Metrics: {metrics}")

if __name__ == "__main__":
    asyncio.run(main())
