import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.events.models import EventOutbox
from app.models.distribution import DistributionJob, DistributionJobStatus
from app.services.distribution_service import DistributionExecutor
from celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="process_event_outbox_task")
def process_event_outbox_task():
    """
    Polls EventOutbox for pending events, executes their projection handlers.
    """
    from celery_app import run_in_worker_loop
    run_in_worker_loop(_async_process_event_outbox_task())

async def _async_process_event_outbox_task():
    from celery_app import get_celery_session
    async with get_celery_session() as db:
        stmt = select(EventOutbox).where(EventOutbox.status == "CREATED").limit(50)
        res = await db.execute(stmt)
        events = res.scalars().all()

        if not events:
            return

        for event in events:
            logger.info(f"Processing EventOutbox ID: {event.id}, Type: {event.event_type}")
            event.status = "DISPATCHING"
            await db.commit()

            try:
                if event.event_type == "ArticlePublished":
                    await handle_article_published(db, event.payload)
                    # Also handle lifecycle updates for published
                    from app.apps.tnt.projectors import ArticleProjector
                    await ArticleProjector().handle_lifecycle_updated(event.payload, db)
                elif event.event_type == "ArticleThumbnailUpdated":
                    await handle_article_thumbnail_updated(db, event.payload)
                elif event.event_type == "ArticleImpactScoreUpdated":
                    await handle_article_impact_score_updated(db, event.payload)
                elif event.event_type in [
                    "ArticleSubmittedForReview", 
                    "ArticleApproved", 
                    "ArticleRejected", 
                    "ArticleScheduled", 
                    "ArticleArchived"
                ]:
                    from app.apps.tnt.projectors import ArticleProjector
                    await ArticleProjector().handle_lifecycle_updated(event.payload, db)
                elif event.event_type == "NewsletterSubscriptionCreated":
                    from app.newsletter.handlers import handle_newsletter_subscription_created
                    await handle_newsletter_subscription_created(db, event.payload, event.id)

                if event.event_type in [
                    "StoryCreated",
                    "ArticleAssignedToStory",
                    "ArticlePublished",
                    "StoriesMerged",
                    "StoryReawakened"
                ]:
                    from app.apps.tnt.projectors import StoryProjector
                    await StoryProjector().handle_timeline_event(event.event_type, event.payload, event.id, db)
                    
                    if event.event_type == "StoriesMerged":
                        from app.apps.tnt.projectors import ArticleProjector
                        await ArticleProjector().handle_stories_merged(event.payload, db)

                event.status = "DELIVERED"
            except Exception as e:
                logger.error(f"Failed to process EventOutbox ID: {event.id}: {e}")
                event.retry_count += 1
                if event.retry_count >= 3:
                    event.status = "DEAD_LETTER"
                else:
                    event.status = "RETRYING"

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
