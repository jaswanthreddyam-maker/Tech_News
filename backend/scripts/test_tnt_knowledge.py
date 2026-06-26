import asyncio
import logging
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.apps.tnt.knowledge_workflow import KnowledgeWorkflow
from app.apps.tnt.projectors import ArticleProjector, KnowledgeGraphProjector
from app.core.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tnt-knowledge-test")

import pytest


@pytest.mark.asyncio
async def test_knowledge():
    workflow = KnowledgeWorkflow()
    projector = KnowledgeGraphProjector()
    article_projector = ArticleProjector()

    # Create a mock article that will trigger the "Apple" branches in our mock capability logic
    mock_article = {
        "id": "mock_apple_article_123",
        "url": "https://techcrunch.com/2026/09/01/apple-announces-iphone-15",
        "title": "Apple announces the highly anticipated iPhone 15 with new AI features",
        "content": "Apple has officially announced the iPhone 15 today. The company released the device featuring advanced Artificial Intelligence capabilities.",
        "hash": "abc123hash",
        "published_at": "2026-09-01T10:00:00Z"
    }

    logger.info(f"Running deterministic TNT Knowledge workflow on article {mock_article['id']}")

    # First, project the article itself so the foreign key constraints are satisfied!
    async with AsyncSessionLocal() as session:
        await article_projector.project(mock_article["id"], mock_article, session)
        logger.info("Projected base article to satisfy FK constraints.")

    # Run the workflow
    knowledge_artifact = await workflow.execute(mock_article)

    logger.info(f"Workflow completed. Found {len(knowledge_artifact.entities)} entities, {len(knowledge_artifact.topics)} topics, {len(knowledge_artifact.timeline)} timeline events, and {len(knowledge_artifact.relationships)} relationships.")

    # Project them
    async with AsyncSessionLocal() as session:
        await projector.project(knowledge_artifact, session)

    logger.info("Knowledge Extraction and Projection Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_knowledge())
