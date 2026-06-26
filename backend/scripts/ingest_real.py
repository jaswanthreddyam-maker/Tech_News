import asyncio
import sys
from app.core.database import AsyncSessionLocal
from app.services.ingestion.pipeline import crawl_single_source_pipeline

async def main():
    print("Starting manual crawl of real-world sources...")
    async with AsyncSessionLocal() as db:
        for sid in [4, 6, 7, 8]:
            try:
                print(f"Crawling source ID {sid}...")
                metrics = await crawl_single_source_pipeline(db, sid)
                print(f"Crawl of source ID {sid} completed. Metrics: {metrics}")
            except Exception as e:
                print(f"Error crawling source ID {sid}: {e}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
