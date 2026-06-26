import asyncio
import logging
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.apps.tnt.ingestion_workflow import IngestionWorkflow
from app.apps.tnt.projectors import ArticleProjector
from app.core.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tnt-ingestion-test")

import pytest


@pytest.mark.asyncio
async def test_ingestion():
    workflow = IngestionWorkflow()
    projector = ArticleProjector()

    # We will test with a known good tech feed
    feed_url = "https://techcrunch.com/feed/"

    logger.info(f"Running deterministic TNT ingestion workflow on {feed_url}")
    # Run the workflow
    published_artifacts = await workflow.execute(feed_url)

    logger.info(f"Published {len(published_artifacts)} artifacts.")

    # Project them
    async with AsyncSessionLocal() as session:
        for result in published_artifacts:
            await projector.project(result["artifact_id"], result["article"], session)

    logger.info("Ingestion and Projection Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_ingestion())
