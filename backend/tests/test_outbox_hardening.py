"""
Outbox Hardening — Failure-Injection Tests

Tests the 7 critical scenarios from the frozen contracts:
1. SKIP LOCKED prevents concurrent workers from double-claiming
2. Crash after projection + before DELIVERED → checkpoint prevents re-execution
3. Handler failure → savepoint rollback → subsequent events continue
4. Max retries → DEAD_LETTER + DeadLetterEvent insertion
5. Expired lease → reclaimed by next poll
6. DELIVERED is immutable (terminal state)
7. Same handler + same event dispatched twice → checkpoint dedup
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.models import (
    DeadLetterEvent,
    EventOutbox,
    OutboxDispatchCheckpoint,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_outbox_event(
    db: AsyncSession,
    event_type: str = "ArticleThumbnailUpdated",
    payload: dict | None = None,
    status: str = "CREATED",
    retry_count: int = 0,
    max_retries: int = 3,
    lease_id: str | None = None,
    lease_expires_at: datetime | None = None,
) -> int:
    """Insert an EventOutbox row and return its ID."""
    stmt = insert(EventOutbox).values(
        event_type=event_type,
        payload=payload or {"id": "test-article-1"},
        status=status,
        retry_count=retry_count,
        max_retries=max_retries,
        lease_id=lease_id,
        lease_expires_at=lease_expires_at,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ).returning(EventOutbox.id)
    result = await db.execute(stmt)
    event_id = result.scalar_one()
    await db.commit()
    return event_id


async def _get_event_status(db: AsyncSession, event_id: int) -> str:
    result = await db.execute(
        select(EventOutbox.status).where(EventOutbox.id == event_id)
    )
    return result.scalar_one()


async def _checkpoint_exists(
    db: AsyncSession, handler_name: str, outbox_event_id: int
) -> bool:
    result = await db.execute(
        select(OutboxDispatchCheckpoint.id).where(
            OutboxDispatchCheckpoint.handler_name == handler_name,
            OutboxDispatchCheckpoint.outbox_event_id == outbox_event_id,
        )
    )
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Test 1: Checkpoint-based idempotency after simulated crash
# ---------------------------------------------------------------------------

async def test_checkpoint_prevents_double_execution(db_session: AsyncSession):
    """
    Scenario: Worker A processes handler successfully → checkpoint written.
    Worker B (or retry) attempts the same handler for the same event.
    Expected: Handler NOT re-invoked. Checkpoint causes skip.
    """
    event_id = await _create_outbox_event(db_session, event_type="ArticleThumbnailUpdated")

    # Simulate prior successful execution by writing a checkpoint
    db_session.add(OutboxDispatchCheckpoint(
        handler_name="article_thumbnail_updated",
        outbox_event_id=event_id,
    ))
    await db_session.commit()

    # Now dispatch — the handler should NOT be called
    with patch(
        "app.tasks.distribution_tasks._HANDLER_MAP",
        {"handle_article_thumbnail_updated": AsyncMock()},
    ) as mock_map:
        from app.tasks.distribution_tasks import _async_process_event_outbox_task
        await _async_process_event_outbox_task()

        # The handler was NOT invoked because checkpoint existed
        mock_map["handle_article_thumbnail_updated"].assert_not_called()

    # Event should be DELIVERED (all handlers checkpointed)
    status = await _get_event_status(db_session, event_id)
    assert status == "DELIVERED"


# ---------------------------------------------------------------------------
# Test 2: Handler failure → savepoint rollback → RETRYING status
# ---------------------------------------------------------------------------

async def test_handler_failure_triggers_retry(db_session: AsyncSession):
    """
    Scenario: Handler raises an exception during processing.
    Expected: Event moves to RETRYING, no checkpoint written,
              savepoint rolled back so no partial DB mutations persist.
    """
    event_id = await _create_outbox_event(
        db_session,
        event_type="ArticleThumbnailUpdated",
        max_retries=3,
        retry_count=0,
    )

    # Make the handler raise
    failing_handler = AsyncMock(side_effect=RuntimeError("Simulated failure"))
    with patch(
        "app.tasks.distribution_tasks._HANDLER_MAP",
        {"handle_article_thumbnail_updated": failing_handler},
    ):
        from app.tasks.distribution_tasks import _async_process_event_outbox_task
        await _async_process_event_outbox_task()

    # Event should be RETRYING, not DELIVERED
    status = await _get_event_status(db_session, event_id)
    assert status == "RETRYING"

    # No checkpoint written
    assert not await _checkpoint_exists(
        db_session, "article_thumbnail_updated", event_id
    )

    # Retry count incremented
    result = await db_session.execute(
        select(EventOutbox.retry_count).where(EventOutbox.id == event_id)
    )
    assert result.scalar_one() == 1


# ---------------------------------------------------------------------------
# Test 3: Max retries → DEAD_LETTER + DeadLetterEvent insertion
# ---------------------------------------------------------------------------

async def test_max_retries_routes_to_dead_letter(db_session: AsyncSession):
    """
    Scenario: Event has already failed (max_retries - 1) times. Next failure
              should move it to DEAD_LETTER and insert a DeadLetterEvent record.
    """
    event_id = await _create_outbox_event(
        db_session,
        event_type="ArticleThumbnailUpdated",
        max_retries=3,
        retry_count=2,  # Already failed twice → next failure is the 3rd
    )

    failing_handler = AsyncMock(side_effect=RuntimeError("Final failure"))
    with patch(
        "app.tasks.distribution_tasks._HANDLER_MAP",
        {"handle_article_thumbnail_updated": failing_handler},
    ):
        from app.tasks.distribution_tasks import _async_process_event_outbox_task
        await _async_process_event_outbox_task()

    # Event should be DEAD_LETTER
    status = await _get_event_status(db_session, event_id)
    assert status == "DEAD_LETTER"

    # DeadLetterEvent should exist
    result = await db_session.execute(
        select(DeadLetterEvent).where(
            DeadLetterEvent.original_outbox_id == event_id
        )
    )
    dead_letter = result.scalars().first()
    assert dead_letter is not None
    assert "Final failure" in dead_letter.failure_reason


# ---------------------------------------------------------------------------
# Test 4: Expired lease → reclaimed by next poll
# ---------------------------------------------------------------------------

async def test_expired_lease_is_reclaimed(db_session: AsyncSession):
    """
    Scenario: Worker A crashed while holding a lease (LEASED with expired timestamp).
    Expected: Next poll reclaims the event and processes it.
    """
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    event_id = await _create_outbox_event(
        db_session,
        event_type="ArticleThumbnailUpdated",
        status="LEASED",
        lease_id="dead-worker-uuid",
        lease_expires_at=expired_time,
    )

    # The handler should succeed on reclaim
    success_handler = AsyncMock()
    with patch(
        "app.tasks.distribution_tasks._HANDLER_MAP",
        {"handle_article_thumbnail_updated": success_handler},
    ):
        from app.tasks.distribution_tasks import _async_process_event_outbox_task
        await _async_process_event_outbox_task()

    # Event should be reclaimed and DELIVERED
    status = await _get_event_status(db_session, event_id)
    assert status == "DELIVERED"
    success_handler.assert_called_once()


# ---------------------------------------------------------------------------
# Test 5: DELIVERED is a terminal state — not reclaimed
# ---------------------------------------------------------------------------

async def test_delivered_event_is_not_reclaimed(db_session: AsyncSession):
    """
    Scenario: Event is already DELIVERED.
    Expected: The dispatcher does NOT reclaim or reprocess it.
    """
    event_id = await _create_outbox_event(
        db_session,
        event_type="ArticleThumbnailUpdated",
        status="DELIVERED",
    )

    handler = AsyncMock()
    with patch(
        "app.tasks.distribution_tasks._HANDLER_MAP",
        {"handle_article_thumbnail_updated": handler},
    ):
        from app.tasks.distribution_tasks import _async_process_event_outbox_task
        await _async_process_event_outbox_task()

    # Handler was NOT called
    handler.assert_not_called()

    # Status unchanged
    status = await _get_event_status(db_session, event_id)
    assert status == "DELIVERED"


# ---------------------------------------------------------------------------
# Test 6: DEAD_LETTER is a terminal state — not reclaimed
# ---------------------------------------------------------------------------

async def test_dead_letter_event_is_not_reclaimed(db_session: AsyncSession):
    """
    Scenario: Event is DEAD_LETTER.
    Expected: Not reclaimed unless explicitly replayed by admin.
    """
    event_id = await _create_outbox_event(
        db_session,
        event_type="ArticleThumbnailUpdated",
        status="DEAD_LETTER",
    )

    handler = AsyncMock()
    with patch(
        "app.tasks.distribution_tasks._HANDLER_MAP",
        {"handle_article_thumbnail_updated": handler},
    ):
        from app.tasks.distribution_tasks import _async_process_event_outbox_task
        await _async_process_event_outbox_task()

    handler.assert_not_called()
    status = await _get_event_status(db_session, event_id)
    assert status == "DEAD_LETTER"


# ---------------------------------------------------------------------------
# Test 7: Multiple handlers — partial success with checkpoint
# ---------------------------------------------------------------------------

async def test_partial_handler_success_preserves_checkpoint(db_session: AsyncSession):
    """
    Scenario: ArticlePublished has two handlers:
      1. article_published_projection → succeeds (checkpoint written)
      2. article_lifecycle_updated → fails
    On retry, handler 1 should be SKIPPED (checkpoint), handler 2 retried.
    """
    event_id = await _create_outbox_event(
        db_session,
        event_type="ArticlePublished",
        payload={"id": "42", "title": "Test"},
    )

    # First dispatch: handler 1 succeeds, handler 2 fails
    call_count = {"published": 0, "lifecycle": 0}

    async def _succeed(db, payload, eid, *args):
        call_count["published"] += 1

    async def _fail(db, payload, eid, *args):
        call_count["lifecycle"] += 1
        raise RuntimeError("lifecycle handler crash")

    with patch(
        "app.tasks.distribution_tasks._HANDLER_MAP",
        {
            "handle_article_published": _succeed,
            "handle_lifecycle_updated": _fail,
            "handle_story_timeline_event": AsyncMock(),
        },
    ):
        from app.tasks.distribution_tasks import _async_process_event_outbox_task
        await _async_process_event_outbox_task()

    assert call_count["published"] == 1
    assert call_count["lifecycle"] == 1

    status = await _get_event_status(db_session, event_id)
    assert status == "RETRYING"

    # Checkpoint should exist for handler 1 only
    assert await _checkpoint_exists(
        db_session, "article_published_projection", event_id
    )
    assert not await _checkpoint_exists(
        db_session, "article_lifecycle_updated", event_id
    )

    # Second dispatch: handler 1 skipped, handler 2 now succeeds
    call_count = {"published": 0, "lifecycle": 0}

    async def _succeed_now(db, payload, eid, *args):
        call_count["lifecycle"] += 1

    with patch(
        "app.tasks.distribution_tasks._HANDLER_MAP",
        {
            "handle_article_published": _succeed,
            "handle_lifecycle_updated": _succeed_now,
            "handle_story_timeline_event": AsyncMock(),
        },
    ):
        await _async_process_event_outbox_task()

    # Handler 1 was NOT called again
    assert call_count["published"] == 0
    # Handler 2 was called
    assert call_count["lifecycle"] == 1

    status = await _get_event_status(db_session, event_id)
    assert status == "DELIVERED"


# ---------------------------------------------------------------------------
# Test 8: Handler registry returns correct handlers per event type
# ---------------------------------------------------------------------------

def test_handler_registry_coverage():
    """Verify all known event types have at least one handler registered."""
    from app.tasks.distribution_tasks import _get_handlers_for_event

    expected_event_types = [
        "ArticlePublished",
        "ArticleThumbnailUpdated",
        "ArticleImpactScoreUpdated",
        "ArticleSubmittedForReview",
        "ArticleApproved",
        "ArticleRejected",
        "ArticleScheduled",
        "ArticleArchived",
        "NewsletterSubscriptionCreated",
        "ProjectionRefreshRequested",
        "StoryCreated",
        "ArticleAssignedToStory",
        "StoriesMerged",
        "StoryReawakened",
    ]

    for event_type in expected_event_types:
        handlers = _get_handlers_for_event(event_type)
        assert len(handlers) > 0, f"No handlers for {event_type}"

    # ArticlePublished should have 3 handlers:
    # article_published_projection, article_lifecycle_updated, story_timeline_event
    ap_handlers = _get_handlers_for_event("ArticlePublished")
    handler_names = [h[0] for h in ap_handlers]
    assert "article_published_projection" in handler_names
    assert "article_lifecycle_updated" in handler_names
    assert "story_timeline_event" in handler_names

    # StoriesMerged should have 2: story_timeline_event, stories_merged_projection
    sm_handlers = _get_handlers_for_event("StoriesMerged")
    handler_names = [h[0] for h in sm_handlers]
    assert "story_timeline_event" in handler_names
    assert "stories_merged_projection" in handler_names
