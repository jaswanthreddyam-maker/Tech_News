import logging
from datetime import datetime, timezone
from celery import shared_task

from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.models.story import Story, StoryStatus
from app.models.analytics import ArticleMetrics, StoryTelemetrySnapshot
from app.models.article import ArticleReadModel
from app.models.user import SavedArticle

logger = logging.getLogger(__name__)

@shared_task(name="capture_story_telemetry_snapshots")
def capture_story_telemetry_snapshots():
    """
    Runs hourly to snapshot the performance of all ACTIVE and MONITORING stories.
    Aggregates data from underlying ArticleMetrics.
    """
async def capture_snapshots_async(session=None):
    from celery_app import get_celery_session
    
    is_managed_session = session is not None
    session_ctx = session if is_managed_session else get_celery_session()
    
    if not is_managed_session:
        await session_ctx.__aenter__()

    try:
        # 1. Find all eligible stories
        stmt = select(Story).where(Story.status.in_([StoryStatus.ACTIVE, StoryStatus.MONITORING]))
        result = await session_ctx.execute(stmt)
        stories = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        snapshots = []

        for story in stories:
            created_at = story.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            age_delta = now - created_at
            age_hours = max(0.0, age_delta.total_seconds() / 3600.0)
            
            # Find all underlying articles
            art_stmt = select(ArticleReadModel.id).where(ArticleReadModel.story_id == str(story.id))
            art_res = await session_ctx.execute(art_stmt)
            article_ids = art_res.scalars().all()
            
            article_count = len(article_ids)
            if article_count == 0:
                continue
                
            metrics_stmt = select(
                func.sum(ArticleMetrics.views).label("total_views"),
                func.sum(ArticleMetrics.unique_views).label("total_unique_views"),
                func.avg(ArticleMetrics.avg_read_time_seconds).label("avg_read_time"),
                func.avg(ArticleMetrics.completion_rate).label("avg_completion")
            ).where(ArticleMetrics.article_id.in_(article_ids))
            
            metrics_res = await session_ctx.execute(metrics_stmt)
            metrics_row = metrics_res.first()
            
            total_views = metrics_row.total_views or 0
            total_unique_readers = metrics_row.total_unique_views or 0
            avg_read_time = metrics_row.avg_read_time or 0.0
            avg_comp_rate = metrics_row.avg_completion or 0.0
            
            bookmarks_stmt = select(func.count(SavedArticle.id)).where(SavedArticle.article_id.in_(article_ids))
            bookmarks_res = await session_ctx.execute(bookmarks_stmt)
            total_bookmarks = bookmarks_res.scalar() or 0
            
            from app.models.story import StoryTimelineEvent
            reawaken_stmt = select(func.count(StoryTimelineEvent.id)).where(
                StoryTimelineEvent.story_id == str(story.id),
                StoryTimelineEvent.event_type == 'StoryReawakened'
            )
            reawaken_res = await session_ctx.execute(reawaken_stmt)
            total_reawakens = reawaken_res.scalar() or 0
            
            total_newsletter_clicks = 0 
            total_newsletter_deliveries = 0
            
            snapshot = StoryTelemetrySnapshot(
                story_id=str(story.id),
                captured_at=now,
                story_status=story.status.value,
                story_age_hours=age_hours,
                views=total_views,
                unique_readers=total_unique_readers,
                avg_read_time_seconds=avg_read_time,
                avg_completion_rate=avg_comp_rate,
                reawaken_count=total_reawakens,
                bookmarks=total_bookmarks,
                newsletter_deliveries=total_newsletter_deliveries,
                newsletter_clicks=total_newsletter_clicks,
                article_count=article_count,
                snapshot_version=1
            )
            
            snapshots.append(snapshot)
        
        if snapshots:
            session_ctx.add_all(snapshots)
            await session_ctx.commit()
            logger.info(f"Successfully captured {len(snapshots)} story telemetry snapshots.")
            
    except Exception as e:
        logger.error(f"Failed to capture story telemetry snapshots: {e}")
        await session_ctx.rollback()
    finally:
        if not is_managed_session:
            await session_ctx.__aexit__(None, None, None)

@shared_task(name="capture_story_telemetry_snapshots")
def capture_story_telemetry_snapshots():
    from celery_app import run_in_worker_loop
    run_in_worker_loop(capture_snapshots_async())
