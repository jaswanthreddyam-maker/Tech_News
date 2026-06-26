import asyncio
import sys
from app.core.database import AsyncSessionLocal
from app.services.ingestion.pipeline import crawl_single_source_pipeline

async def main():
    print("Starting isolated manual crawl of real-world sources...")
    # Active sources:
    # 3: NVIDIA AI Blog
    # 4: Google DeepMind
    # 5: TechCrunch
    # 6: The Verge
    # 7: Ars Technica
    # 1: OpenAI Blog
    # 2: Anthropic News
    for sid in [3, 4, 5, 6, 7]:
        try:
            print(f"\n=========================================")
            print(f"Crawling source ID {sid}...")
            print(f"=========================================")
            async with AsyncSessionLocal() as db:
                metrics = await crawl_single_source_pipeline(db, sid)
                print(f"Crawl of source ID {sid} completed. Metrics: {metrics}")
        except Exception as e:
            print(f"Error crawling source ID {sid}: {e}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
