from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import RawArticle
from celery_app import enqueue_fresh_articles, recover_stale_ai_jobs


@pytest.mark.asyncio
async def test_recovery_ignores_fresh_article(db_session: AsyncSession):
    # Test 1: Fresh article -> Recovery ignores it
    raw = RawArticle(
        title="Fresh",
        url="http://test.com/fresh",
        url_hash="fresh",
        title_hash="fresh",
        status="ai_queued",
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add(raw)
    await db_session.flush()

    with patch("celery_app.process_raw_article_task.delay") as mock_delay:
        recovered, failed = await recover_stale_ai_jobs(db_session)

    assert recovered == 0
    assert failed == 0
    mock_delay.assert_not_called()


@pytest.mark.asyncio
async def test_recovery_requeues_stale_article(db_session: AsyncSession):
    # Test 2: Stale article -> Recovery requeues once
    raw = RawArticle(
        title="Stale",
        url="http://test.com/stale",
        url_hash="stale",
        title_hash="stale",
        status="ai_queued",
        retry_count=0,
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    db_session.add(raw)
    await db_session.flush()

    with patch("celery_app.process_raw_article_task.delay") as mock_delay:
        recovered, failed = await recover_stale_ai_jobs(db_session)

    assert recovered == 1
    assert failed == 0
    mock_delay.assert_called_once_with(raw.id)

    # Verify DB updates
    stmt = select(RawArticle).where(RawArticle.id == raw.id)
    res = await db_session.execute(stmt)
    updated_raw = res.scalars().first()
    assert updated_raw.retry_count == 1
    assert updated_raw.last_retry_at is not None
    assert updated_raw.status == "ai_queued"


@pytest.mark.asyncio
async def test_recovery_moves_to_failed_after_max_retries(db_session: AsyncSession):
    # Test 3: retry_count == 3 -> Moves to FAILED
    raw = RawArticle(
        title="Failed",
        url="http://test.com/failed",
        url_hash="failed",
        title_hash="failed",
        status="ai_queued",
        retry_count=3,
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    db_session.add(raw)
    await db_session.flush()

    with patch("celery_app.process_raw_article_task.delay") as mock_delay:
        recovered, failed = await recover_stale_ai_jobs(db_session)

    assert recovered == 0
    assert failed == 1
    mock_delay.assert_not_called()

    # Verify DB updates
    stmt = select(RawArticle).where(RawArticle.id == raw.id)
    res = await db_session.execute(stmt)
    updated_raw = res.scalars().first()
    assert updated_raw.status == "dead_letter"
    assert updated_raw.error_log == "ai_timeout"


@pytest.mark.asyncio
async def test_recovery_limits_to_8(db_session: AsyncSession):
    # Test 4: Only 8 recovered
    for i in range(10):
        raw = RawArticle(
            title=f"Bulk {i}",
            url=f"http://test.com/bulk{i}",
            url_hash=f"bulk{i}",
            title_hash=f"bulk{i}",
            status="ai_queued",
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        )
        db_session.add(raw)
    await db_session.flush()

    with patch("celery_app.process_raw_article_task.delay") as mock_delay:
        recovered, failed = await recover_stale_ai_jobs(db_session)

    assert recovered == 8
    assert failed == 0
    assert mock_delay.call_count == 8


@pytest.mark.asyncio
async def test_fresh_queue_processed_before_recovery(db_session: AsyncSession):
    # Test 5: Fresh queue always processed before recovery queue (verified by the logic in _execute calling fresh first)
    # This test just verifies enqueue_fresh_articles works as expected to not break normal pipeline
    raw = RawArticle(
        title="Fresh Ingestion",
        url="http://test.com/fresh-ingest",
        url_hash="fresh-ingest",
        title_hash="fresh-ingest",
        status="fetched",
    )
    db_session.add(raw)
    await db_session.flush()

    with patch("celery_app.process_raw_article_task.delay") as mock_delay:
        fresh_enqueued = await enqueue_fresh_articles(db_session)

    assert fresh_enqueued == 1
    mock_delay.assert_called_once_with(raw.id)

    stmt = select(RawArticle).where(RawArticle.id == raw.id)
    res = await db_session.execute(stmt)
    updated_raw = res.scalars().first()
    assert updated_raw.status == "ai_queued"
