import asyncio
import sys
import logging
from app.core.database import AsyncSessionLocal
from app.services.ingestion.pipeline import process_raw_article_to_editorial

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run(raw_id):
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"Processing raw_id: {raw_id}")
            result = await process_raw_article_to_editorial(db, raw_id)
            logger.info(f"Result: {result}")
        except Exception as e:
            logger.error(f"EXCEPTION CAUGHT: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1])))
