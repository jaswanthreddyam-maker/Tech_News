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
        for draft in drafts:
            logger.info(f"Publishing scheduled draft: {draft.id} - {draft.title}")
            try:
                await pipeline.publish(draft.id)
                logger.info(f"Successfully published scheduled draft: {draft.id}")
            except Exception as e:
                logger.error(f"Failed to publish scheduled draft {draft.id}: {e}")
