import asyncio
from app.db.session import async_session_maker
from app.services.ingestion.pipeline import run_source_ingestion_pipeline
import logging
logging.basicConfig(level=logging.INFO)

async def main():
    async with async_session_maker() as db:
        res = await run_source_ingestion_pipeline(db)
        print("PIPELINE RESULT:")
        print(res)

if __name__ == "__main__":
    asyncio.run(main())
