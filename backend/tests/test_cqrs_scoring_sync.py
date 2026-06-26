import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.tnt.projectors import ArticleProjector
from app.core.events.schemas import ArticlePublishedPayload
from app.models.article import ArticleReadModel


@pytest.mark.asyncio
async def test_cqrs_scoring_sync_full_pipeline(db_session: AsyncSession):
    """
    Regression test to ensure scoring fields flow properly from the 
    ArticlePublishedPayload contract to the ArticleReadModel projector.
    """
    # 1. Simulate the Pipeline creating the Payload (the Contract)
    payload = ArticlePublishedPayload(
        id="9999",
        url="test-scoring-sync-slug",
        title="Test Scoring Sync",
        content="Test content",
        summary="Test summary",
        hash="test_hash_123",
        source="Test Source",
        published_at=datetime.now(timezone.utc),
        impact_score=85.5,
        freshness_score=0.9,
        engagement_score=1.2,
        final_score=92.34,
        category="AI",
        published_status="published",
        is_test_data=True
    )
    
    # 2. Simulate the Outbox Processor invoking the Projector
    projector = ArticleProjector()
    await projector.project(
        artifact_id=payload.id,
        article_data=payload.model_dump(mode="json"),
        session=db_session
    )
    
    # 3. Assert the Read Model correctly received and mapped the fields
    stmt = select(ArticleReadModel).where(ArticleReadModel.id == "9999")
    res = await db_session.execute(stmt)
    read_model = res.scalars().first()
    
    assert read_model is not None
    assert float(read_model.final_score) == 92.34
    assert float(read_model.freshness_score) == 0.9
    assert float(read_model.engagement_score) == 1.2
    assert float(read_model.final_score) == 92.34
    assert read_model.category == "AI"
    assert read_model.published_status == "published"
