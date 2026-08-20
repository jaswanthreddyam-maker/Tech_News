import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.editorial import EditorialDraft, EditorialDraftStatus
from app.services.editorial_service import PublishingPipeline
from celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="check_and_publish_scheduled_drafts_task")
def check_and_publish_scheduled_drafts_task():
    """
    Checks for SCHEDULED drafts where publish_at <= now, and publishes them.
    This runs via Celery Beat every minute.
    """
    from celery_app import run_in_worker_loop
    run_in_worker_loop(_async_check_and_publish_scheduled_drafts_task())

async def _async_check_and_publish_scheduled_drafts_task():
    logger.info("Checking for scheduled editorial drafts...")
    from celery_app import get_celery_session
    async with get_celery_session() as db:
        now = datetime.now(timezone.utc)
        stmt = select(EditorialDraft).where(
            EditorialDraft.status == EditorialDraftStatus.SCHEDULED.value,
            EditorialDraft.publish_at <= now
        )
        result = await db.execute(stmt)
        drafts = result.scalars().all()

        if not drafts:
            logger.info("No scheduled drafts ready to publish.")
            return

        pipeline = PublishingPipeline(db)
        published_count = 0
        for draft in drafts:
            logger.info(f"Publishing scheduled draft: {draft.id} - {draft.title}")
            try:
                await pipeline.publish(draft.id)
                published_count += 1
                logger.info(f"Successfully published scheduled draft: {draft.id}")
            except Exception as e:
                logger.error(f"Failed to publish scheduled draft {draft.id}: {e}")

        # Guardrail 2: Batch cache invalidation ONCE after loop finishes ONLY if state changed
        if published_count > 0:
            from app.services.cache_service import CacheService
            await CacheService.invalidate_homepage_cache(reason=f"published_{published_count}_scheduled_drafts")

@celery_app.task(name="tasks.editorial.purge_expired_articles")
def purge_expired_articles_task():
    """
    Purges expired articles every minute.
    """
    from celery_app import run_in_worker_loop
    run_in_worker_loop(_async_purge_expired_articles_task())

async def _async_purge_expired_articles_task():
    logger.info("Starting expired articles expiration loop...")
    from app.services.ranking.news_ranking_engine import expire_articles
    from app.editorial.homepage_builder import HomepageBuilder
    from app.services.cache_service import CacheService
    from app.services.ingestion.replenishment import AutoReplenishmentService
    from celery_app import get_celery_session

    async with get_celery_session() as db:
        metrics = await expire_articles(db)
        if metrics.get("expired_articles_total", 0) > 0:
            logger.info(f"Expiration complete. Metrics: {metrics}. Rebuilding projection.")
            await HomepageBuilder.build_and_persist_homepage_projection(db)
            await HomepageBuilder.build_and_persist_category_desks(db)
            await CacheService.invalidate_homepage_cache(reason=f"expired_{metrics['expired_articles_total']}_articles")

        # Actively ensure fresh article inventory is above the minimum floor; self-heal immediately
        try:
            repl_res = await AutoReplenishmentService.trigger_replenishment_if_needed(db)
            if repl_res.get("triggered"):
                logger.info(f"AutoReplenishment executed during purge cycle: {repl_res}")
        except Exception as e:
            logger.warning(f"AutoReplenishment failed during purge cycle: {e}")

