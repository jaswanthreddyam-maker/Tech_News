from datetime import datetime, timezone

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.models import EventOutbox
from app.models.article import ArticleReadModel, ProcessedArticle
from app.models.workspace import Workspace
from app.models.editorial import PublicationRecord
from app.services.ingestion.thumbnail_service import ThumbnailUpdatedApplicationService
from app.tasks.distribution_tasks import _async_process_event_outbox_task

pytestmark = pytest.mark.asyncio

from app.models.article import Category, RawArticle
from app.models.source import Source


async def test_thumbnail_cqrs_lifecycle(db_session: AsyncSession):
    # Setup Category and Source
    import uuid
    uid = uuid.uuid4().hex[:6]
    cat = Category(name=f"Test Category {uid}", slug=f"test-cat-{uid}")
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)

    src = Source(name=f"Test Source {uid}", url=f"http://test.com/{uid}", category="Technology", method="rss")
    db_session.add(src)
    await db_session.commit()
    await db_session.refresh(src)

    # Setup RawArticle
    raw = RawArticle(
        source_id=src.id,
        url=f"http://test.com/raw-{uid}",
        url_hash=f"urlhash-{uid}",
        title=f"Test {uid}",
        title_hash=f"titlehash-{uid}",
        status="processed"
    )
    db_session.add(raw)
    await db_session.commit()
    await db_session.refresh(raw)

    # 1. Setup ProcessedArticle
    pa = ProcessedArticle(
        raw_article_id=raw.id,
        source_id=src.id,
        category_id=cat.id,
        slug=f"test-thumbnail-cqrs-{uid}",
        title=f"Thumbnail CQRS Test {uid}",
        summary="Test",
        content="Test content",
        source="System",
        source_name="System",
        published_at=datetime.now(timezone.utc),
        published_status="published",
        is_test_data=True
    )
    db_session.add(pa)
    await db_session.commit()
    await db_session.refresh(pa)

    # 2. Setup Initial ArticleReadModel (simulating an ArticlePublished event that already ran)
    artifact_id = str(pa.id)
    stmt = insert(ArticleReadModel).values(
        id=artifact_id,
        url=f"https://technewstoday.com/articles/test-thumbnail-cqrs-{uid}",
        title=pa.title,
        content=pa.content,
        hash="old_hash",
        source="System",
        thumbnail_local=None,
        thumbnail_url=None,
        is_test_data=True
    )
    await db_session.execute(stmt)
    await db_session.commit()

    # 3. Simulate Thumbnail Downloading
    await ThumbnailUpdatedApplicationService.finalize_thumbnail_update(
        db=db_session,
        article_id=pa.id,
        thumbnail_url="/images/fallback-news.webp",
        thumbnail_local="/images/fallback-news.webp",
        thumbnail_hash="fallback_hash",
        thumbnail_source="fallback",
        candidate_count=0,
        winner_pass="fallback",
        thumbnail_score=0
    )

    # Verify EventOutbox was created
    outbox_stmt = select(EventOutbox).where(EventOutbox.event_type == "ArticleThumbnailUpdated")
    outbox_res = await db_session.execute(outbox_stmt)
    outbox_events = outbox_res.scalars().all()

    assert len(outbox_events) == 1
    event = outbox_events[0]
    assert event.payload["article_id"] == artifact_id
    assert event.payload["thumbnail_local"] == "/images/fallback-news.webp"
    assert event.status == "CREATED"

    # 4. Process EventOutbox (this should route to ArticleProjector.handle_thumbnail_updated)
    await _async_process_event_outbox_task()

    # 5. Verify Read Model Update
    read_stmt = select(ArticleReadModel).where(ArticleReadModel.id == artifact_id)
    read_res = await db_session.execute(read_stmt)
    read_model = read_res.scalars().first()

    assert read_model is not None
    assert read_model.thumbnail_local == "/images/fallback-news.webp"
    assert read_model.thumbnail_url == "/images/fallback-news.webp"
    assert read_model.hash == "fallback_hash"
    assert read_model.title == f"Thumbnail CQRS Test {uid}" # other fields preserved

    # 6. Verify EventOutbox status changed to DELIVERED (full async pipeline confirmation)
    db_session.expire_all()
    delivered_stmt = select(EventOutbox).where(
        EventOutbox.event_type == "ArticleThumbnailUpdated",
        EventOutbox.status == "DELIVERED"
    )
    delivered_res = await db_session.execute(delivered_stmt)
    delivered_events = delivered_res.scalars().all()
    assert len(delivered_events) == 1, f"Expected 1 DELIVERED event, got {len(delivered_events)}"
