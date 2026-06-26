import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO)


async def main():
    print("Manual Trigger: Starting real-time RSS news ingestion pipeline...")
    from app.core.database import AsyncSessionLocal
    from app.services.ingestion.pipeline import run_source_ingestion_pipeline

    async with AsyncSessionLocal() as db:
        try:
            metrics = await run_source_ingestion_pipeline(db)
            print("=" * 60)
            print("CRAWL COMPLETE! METRICS SUMMARY:")
            print("=" * 60)
            for k, v in metrics.items():
                print(f" - {k.replace('_', ' ').title()}: {v}")
            print("=" * 60)
        except Exception as e:
            print(f"CRITICAL: Ingestion pipeline execution failed: {e!s}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
