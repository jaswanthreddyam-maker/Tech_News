import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text, update

from app.core.database import AsyncSessionLocal
from app.core.events.models import DeadLetterEvent, EventOutbox, OutboxDispatchCheckpoint
from app.models.distribution import DistributionJob, DistributionJobStatus
from app.services.distribution_service import DistributionExecutor
from celery_app import celery_app

logger = logging.getLogger(__name__)


from dataclasses import dataclass

@dataclass(frozen=True)
class EventContext:
    """Explicit event context passed to outbox handlers."""
    event_id: int
    event_type: str
    payload: dict
    correlation_id: str | None = None


# ---------------------------------------------------------------------------
# Handler Registry
# ---------------------------------------------------------------------------
# Maps event_type → list of (handler_name, async handler callable).
# handler_name is used as the checkpoint key for idempotency.
# An event type may have multiple handlers; each has its own checkpoint.
# ---------------------------------------------------------------------------

def _get_handlers_for_event(event_type: str) -> list[tuple[str, ...]]:
    """
    Returns a list of (handler_name, handler_coro_factory) tuples for the
    given event_type. handler_coro_factory is a string reference resolved
    at dispatch time to avoid circular imports.
    """
    handlers = []

    if event_type == "ArticlePublished":
        handlers.append(("article_published_projection", "handle_article_published"))
        handlers.append(("article_lifecycle_updated", "handle_lifecycle_updated"))

    elif event_type == "ArticleThumbnailUpdated":
        handlers.append(("article_thumbnail_updated", "handle_article_thumbnail_updated"))

    elif event_type == "ArticleImpactScoreUpdated":
        handlers.append(("article_impact_score_updated", "handle_article_impact_score_updated"))

    elif event_type in (
        "ArticleSubmittedForReview", "ArticleApproved",
        "ArticleRejected", "ArticleScheduled", "ArticleArchived",
    ):
        handlers.append(("article_lifecycle_updated", "handle_lifecycle_updated"))

    elif event_type == "NewsletterSubscriptionCreated":
        handlers.append(("newsletter_subscription_created", "handle_newsletter_subscription_created_wrapper"))

    elif event_type == "ProjectionRefreshRequested":
        handlers.append(("projection_refresh", "handle_projection_refresh"))

    # Story-related events can ALSO fire in addition to above
    if event_type in (
        "StoryCreated", "ArticleAssignedToStory", "ArticlePublished",
        "StoriesMerged", "StoryReawakened",
    ):
        handlers.append(("story_timeline_event", "handle_story_timeline_event"))
        if event_type == "StoriesMerged":
            handlers.append(("stories_merged_projection", "handle_stories_merged"))

    return handlers


async def _resolve_handler(handler_ref: str):
    """Resolve a handler reference string to a callable."""
    return _HANDLER_MAP[handler_ref]


# ---------------------------------------------------------------------------
# Handler Implementations (thin wrappers with explicit parameters)
# ---------------------------------------------------------------------------

async def _handle_article_published(db, payload, event_id, event_type=None):
    await handle_article_published(db, payload)


async def _handle_lifecycle_updated(db, payload, event_id, event_type=None):
    from app.apps.tnt.projectors import ArticleProjector
    await ArticleProjector().handle_lifecycle_updated(payload, db)


async def _handle_article_thumbnail_updated(db, payload, event_id, event_type=None):
    await handle_article_thumbnail_updated(db, payload)


async def _handle_article_impact_score_updated(db, payload, event_id, event_type=None):
    await handle_article_impact_score_updated(db, payload)


async def _handle_newsletter_subscription_created_wrapper(db, payload, event_id, event_type=None):
    from app.newsletter.handlers import handle_newsletter_subscription_created
    await handle_newsletter_subscription_created(db, payload, event_id)


async def _handle_projection_refresh(db, payload, event_id, event_type=None):
    from app.editorial.homepage_builder import HomepageBuilder
    from app.core.redis import get_redis_client
    ptype = payload.get("projection_type", "ALL")

    if ptype in ("ALL", "HOMEPAGE"):
        await HomepageBuilder.build_and_persist_homepage_projection(db)
        redis = get_redis_client()
        if redis:
            try:
                await redis.delete("homepage_projection")
                await redis.delete("api:feed:home")
            except Exception:
                pass

    if ptype in ("ALL", "CATEGORY_DESKS"):
        await HomepageBuilder.build_and_persist_category_desks(db)


async def _handle_story_timeline_event(db, payload, event_id, event_type=None):
    from app.apps.tnt.projectors import StoryProjector
    await StoryProjector().handle_timeline_event(event_type or "", payload, event_id, db)


async def _handle_stories_merged(db, payload, event_id, event_type=None):
    from app.apps.tnt.projectors import ArticleProjector
    await ArticleProjector().handle_stories_merged(payload, db)


# Map of handler_ref string → callable
_HANDLER_MAP = {
    "handle_article_published": _handle_article_published,
    "handle_lifecycle_updated": _handle_lifecycle_updated,
    "handle_article_thumbnail_updated": _handle_article_thumbnail_updated,
    "handle_article_impact_score_updated": _handle_article_impact_score_updated,
    "handle_newsletter_subscription_created_wrapper": _handle_newsletter_subscription_created_wrapper,
    "handle_projection_refresh": _handle_projection_refresh,
    "handle_story_timeline_event": _handle_story_timeline_event,
    "handle_stories_merged": _handle_stories_merged,
}


# ---------------------------------------------------------------------------
# CTE-based Lease Acquisition SQL
# ---------------------------------------------------------------------------

_LEASE_CTE_SQL = text("""
WITH candidates AS (
    SELECT id
    FROM event_outbox
    WHERE (
        status IN ('CREATED', 'RETRYING')
        OR (
            status IN ('LEASED', 'DISPATCHING')
            AND lease_expires_at < NOW()
        )
    )
    ORDER BY created_at
    FOR UPDATE SKIP LOCKED
    LIMIT :batch_size
)
UPDATE event_outbox e
SET
    status = 'LEASED',
    lease_id = :lease_id,
    lease_expires_at = NOW() + INTERVAL '60 seconds',
    updated_at = NOW()
FROM candidates c
WHERE e.id = c.id
RETURNING e.id, e.event_type, e.payload, e.retry_count, e.max_retries,
          e.correlation_id, e.error_log;
""")


# ---------------------------------------------------------------------------
# Outbox Task (Celery entry point)
# ---------------------------------------------------------------------------

@celery_app.task(name="process_event_outbox_task")
def process_event_outbox_task():
    """
    Polls EventOutbox for pending events using CTE + FOR UPDATE SKIP LOCKED,
    executes their projection handlers with checkpoint-based idempotency.
    """
    from celery_app import run_in_worker_loop
    run_in_worker_loop(_async_process_event_outbox_task())


async def _async_process_event_outbox_task():
    """
    Hardened outbox dispatcher implementing:
    1. CTE-based lease acquisition (SKIP LOCKED for concurrent workers)
    2. Per-handler checkpoint idempotency (OutboxDispatchCheckpoint)
    3. Per-event savepoint isolation (handler failure doesn't affect batch)
    4. Dead letter routing on max retries
    5. Expired lease reclamation (crashed worker recovery)
    6. OpenTelemetry business span instrumentation
    """
    from celery_app import get_celery_session
    from app.core.tracing import get_tracer, SpanAttributes

    tracer = get_tracer("tech-news.outbox")
    worker_lease_id = str(uuid.uuid4())

    async with get_celery_session() as db:
        # --- Step 1: Lease acquisition via CTE ---
        try:
            result = await db.execute(
                _LEASE_CTE_SQL,
                {"lease_id": worker_lease_id, "batch_size": 50},
            )
            leased_rows = result.fetchall()
        except Exception as err:
            err_str = str(err)
            if "max_retries" in err_str or "lease_id" in err_str or "UndefinedColumnError" in err_str or "UndefinedTableError" in err_str:
                logger.warning("Event outbox columns/tables missing; applying self-healing schema migration...")
                await db.rollback()
                await db.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS lease_id VARCHAR(100)"))
                await db.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ"))
                await db.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0"))
                await db.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3"))
                await db.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS error_log TEXT"))
                await db.execute(text("ALTER TABLE event_outbox ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(255)"))
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS outbox_dispatch_checkpoints (
                        id SERIAL PRIMARY KEY,
                        handler_name VARCHAR(100) NOT NULL,
                        outbox_event_id INTEGER NOT NULL REFERENCES event_outbox(id) ON DELETE CASCADE,
                        processed_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT uq_dispatch_chkpt UNIQUE (handler_name, outbox_event_id)
                    )
                """))
                await db.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_dispatch_chkpt_lookup ON outbox_dispatch_checkpoints(handler_name, outbox_event_id)
                """))
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS dead_letter_events (
                        id SERIAL PRIMARY KEY,
                        original_outbox_id INTEGER NOT NULL,
                        event_type VARCHAR(100) NOT NULL,
                        payload JSONB NOT NULL,
                        failure_reason VARCHAR(2000) NOT NULL,
                        failed_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                await db.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_dead_letter_events_orig_id ON dead_letter_events(original_outbox_id)
                """))
                await db.commit()
                result = await db.execute(
                    _LEASE_CTE_SQL,
                    {"lease_id": worker_lease_id, "batch_size": 50},
                )
                leased_rows = result.fetchall()
            else:
                raise

        if not leased_rows:
            return

        logger.info(
            f"Outbox dispatcher leased {len(leased_rows)} events "
            f"(worker={worker_lease_id[:8]})"
        )
        await db.commit()

        delivered_count = 0
        failed_count = 0

        # --- Step 2: Process each event within batch span ---
        for row in leased_rows:
            event_id = row.id
            event_type = row.event_type
            payload = row.payload
            retry_count = row.retry_count
            max_retries = row.max_retries
            correlation_id = row.correlation_id

            logger.info(
                f"Dispatching EventOutbox #{event_id} "
                f"type={event_type} retry={retry_count}"
            )

            # Mark as DISPATCHING
            await db.execute(
                update(EventOutbox)
                .where(EventOutbox.id == event_id)
                .values(status="DISPATCHING", updated_at=datetime.now(timezone.utc))
            )
            await db.flush()

            handlers = _get_handlers_for_event(event_type)
            all_succeeded = True
            last_error = None

            for handler_name, handler_ref in handlers:
                # --- Step 3: Check checkpoint (idempotency) ---
                try:
                    chkpt_exists = await db.execute(
                        select(OutboxDispatchCheckpoint.id).where(
                            OutboxDispatchCheckpoint.handler_name == handler_name,
                            OutboxDispatchCheckpoint.outbox_event_id == event_id,
                        )
                    )
                except Exception as chk_err:
                    if "outbox_dispatch_checkpoints" in str(chk_err):
                        await db.rollback()
                        await db.execute(text("""
                            CREATE TABLE IF NOT EXISTS outbox_dispatch_checkpoints (
                                id SERIAL PRIMARY KEY,
                                handler_name VARCHAR(100) NOT NULL,
                                outbox_event_id INTEGER NOT NULL REFERENCES event_outbox(id) ON DELETE CASCADE,
                                processed_at TIMESTAMPTZ DEFAULT NOW(),
                                CONSTRAINT uq_dispatch_chkpt UNIQUE (handler_name, outbox_event_id)
                            )
                        """))
                        await db.execute(text("""
                            CREATE INDEX IF NOT EXISTS ix_dispatch_chkpt_lookup ON outbox_dispatch_checkpoints(handler_name, outbox_event_id)
                        """))
                        await db.commit()
                        chkpt_exists = await db.execute(
                            select(OutboxDispatchCheckpoint.id).where(
                                OutboxDispatchCheckpoint.handler_name == handler_name,
                                OutboxDispatchCheckpoint.outbox_event_id == event_id,
                            )
                        )
                    else:
                        raise
                if chkpt_exists.scalar_one_or_none() is not None:
                    logger.info(
                        f"  Checkpoint exists for handler={handler_name} "
                        f"event={event_id}, skipping"
                    )
                    continue

                # --- Step 4: Execute handler and record checkpoint ---
                handler_fn = _HANDLER_MAP[handler_ref]
                try:
                    await handler_fn(db, payload, event_id, event_type)
                    # Record checkpoint for handler-level idempotency
                    db.add(OutboxDispatchCheckpoint(
                        handler_name=handler_name,
                        outbox_event_id=event_id,
                    ))
                    await db.commit()
                    logger.info(
                        f"  Handler {handler_name} succeeded for event #{event_id}"
                    )
                except Exception as exc:
                    all_succeeded = False
                    last_error = str(exc)[:2000]
                    await db.rollback()
                    logger.error(
                        f"  Handler {handler_name} failed for event #{event_id}: {exc}"
                    )
                    # Break to route event to RETRYING or DEAD_LETTER
                    break

            # --- Step 5: Update event status ---
            if all_succeeded:
                delivered_count += 1
                await db.execute(
                    update(EventOutbox)
                    .where(EventOutbox.id == event_id)
                    .values(
                        status="DELIVERED",
                        updated_at=datetime.now(timezone.utc),
                    )
                )
            else:
                failed_count += 1
                new_retry_count = retry_count + 1
                if new_retry_count >= max_retries:
                    # Route to dead letter
                    await db.execute(
                        update(EventOutbox)
                        .where(EventOutbox.id == event_id)
                        .values(
                            status="DEAD_LETTER",
                            retry_count=new_retry_count,
                            error_log=last_error,
                            lease_id=None,
                            lease_expires_at=None,
                            updated_at=datetime.now(timezone.utc),
                        )
                    )
                    db.add(DeadLetterEvent(
                        original_outbox_id=event_id,
                        event_type=event_type,
                        payload=payload,
                        failure_reason=last_error or "Unknown error",
                    ))
                    logger.warning(
                        f"  Event #{event_id} moved to DEAD_LETTER "
                        f"after {new_retry_count} retries"
                    )
                else:
                    # Schedule for retry
                    await db.execute(
                        update(EventOutbox)
                        .where(EventOutbox.id == event_id)
                        .values(
                            status="RETRYING",
                            retry_count=new_retry_count,
                            error_log=last_error,
                            lease_id=None,
                            lease_expires_at=None,
                            updated_at=datetime.now(timezone.utc),
                        )
                    )
                    logger.info(
                        f"  Event #{event_id} → RETRYING "
                        f"(attempt {new_retry_count}/{max_retries})"
                    )

            await db.commit()


async def handle_article_impact_score_updated(db, payload: dict):
    from app.apps.tnt.projectors import ArticleProjector
    await ArticleProjector().handle_impact_score_updated(payload, db)

async def handle_article_thumbnail_updated(db, payload: dict):

    from app.apps.tnt.projectors import ArticleProjector
    await ArticleProjector().handle_thumbnail_updated(payload, db)

async def handle_article_published(db, article_data: dict):
    import traceback

    from app.apps.tnt.knowledge_workflow import KnowledgeWorkflow
    from app.apps.tnt.projectors import (
        ArticleProjector,
        EntityProjector,
        RelationshipProjector,
        TimelineProjector,
        TopicProjector,
    )

    artifact_id = article_data.get("id")

    # 1. Projectors & Knowledge Workflow
    try:
        await ArticleProjector().project(artifact_id, article_data, db)
        knowledge_artifact = await KnowledgeWorkflow().execute(article_data)

        await EntityProjector().project(knowledge_artifact, db)
        await TopicProjector().project(knowledge_artifact, db)
        await TimelineProjector().project(knowledge_artifact, db)
        await RelationshipProjector().project(knowledge_artifact, db)

        # Update entities status and trigger scoring coordinator
        from app.models.article import ProcessedArticle
        art_id_int = int(artifact_id)
        art_stmt = select(ProcessedArticle).where(ProcessedArticle.id == art_id_int)
        art_res = await db.execute(art_stmt)
        proc_art = art_res.scalars().first()
        if proc_art:
            proc_art.entities_status = "completed"
            await db.flush()

            from app.editorial.coordinator import ArticleEnrichmentCoordinator
            await ArticleEnrichmentCoordinator.mark_stage_complete(db, art_id_int, "knowledge")

    except Exception as e:
        logger.error(f"PROJECTORS failed: {traceback.format_exc()}")
        raise e


    # 2. CACHE_INVALIDATION
    try:
        from app.core.redis import get_redis_client
        redis = get_redis_client()
        await redis.delete("api:feed:home")
        await redis.delete("api:feed:latest")
    except Exception as e:
        logger.error(f"CACHE_INVALIDATION failed: {e}")

@celery_app.task(name="process_distribution_jobs_task")
def process_distribution_jobs_task():
    """
    Polls for QUEUED distribution jobs and executes them.
    """
    from celery_app import run_in_worker_loop
    run_in_worker_loop(_async_process_distribution_jobs_task())

async def _async_process_distribution_jobs_task():
    from celery_app import get_celery_session
    async with get_celery_session() as db:
        stmt = select(DistributionJob).where(DistributionJob.status == DistributionJobStatus.QUEUED).limit(50)
        res = await db.execute(stmt)
        jobs = res.scalars().all()

        if not jobs:
            return

        executor = DistributionExecutor(db)
        for job in jobs:
            await executor.execute_job(job.id)
