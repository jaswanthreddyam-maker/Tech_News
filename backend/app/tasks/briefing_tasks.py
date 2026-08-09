"""
Daily Briefing Celery Tasks

dispatch_due_briefings:
  - Runs every 5 minutes via Celery Beat
  - Finds all enabled, verified subscribers whose local delivery_time
    falls within the current ±2.5-minute window
  - Creates/reuses today's edition (always at max capacity)
  - Dispatches deliveries; UNIQUE(subscriber_id, edition_id) ensures idempotency

celeryconfig.py (add to your Celery app config):
    from celery.schedules import crontab
    beat_schedule = {
        "dispatch-due-briefings": {
            "task": "app.tasks.briefing_tasks.dispatch_due_briefings",
            "schedule": crontab(minute="*/5"),
        }
    }
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def get_celery_app():
    """Lazy import to avoid circular deps and fail gracefully when Celery unavailable."""
    try:
        from app.tasks.celery_app import celery_app
        return celery_app
    except ImportError:
        return None


def dispatch_due_briefings_task():
    """
    Standalone async function that can be called directly (without Celery)
    for testing or manual invocation.
    """
    import asyncio
    from app.core.database import AsyncSessionLocal
    from app.briefing.service import DailyBriefingService

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await DailyBriefingService.dispatch_due_subscribers(db)
            logger.info(f"dispatch_due_briefings result: {result}")
            return result

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# Register Celery task if Celery is available
# ---------------------------------------------------------------------------

_celery_app = get_celery_app()

if _celery_app is not None:
    @_celery_app.task(
        name="app.tasks.briefing_tasks.dispatch_due_briefings",
        bind=True,
        max_retries=3,
        default_retry_delay=60,
    )
    def dispatch_due_briefings(self):
        """
        Celery task: find subscribers due for delivery in their local timezone
        and dispatch today's Daily Briefing edition.

        Runs every 5 minutes (configured in Celery Beat).
        Delivery window = ±2.5 minutes around subscriber's configured delivery_time.
        UNIQUE(subscriber_id, edition_id) guarantees idempotency.
        """
        import asyncio
        from app.core.database import AsyncSessionLocal
        from app.briefing.service import DailyBriefingService

        async def _run():
            async with AsyncSessionLocal() as db:
                return await DailyBriefingService.dispatch_due_subscribers(db)

        try:
            result = asyncio.run(_run())
            logger.info(f"dispatch_due_briefings: {result}")
            return result
        except Exception as exc:
            logger.error(f"dispatch_due_briefings failed: {exc}")
            raise self.retry(exc=exc)

else:
    # Stub so imports don't break when Celery is not configured
    def dispatch_due_briefings():
        """Stub — Celery not configured. Use dispatch_due_briefings_task() directly."""
        return dispatch_due_briefings_task()
