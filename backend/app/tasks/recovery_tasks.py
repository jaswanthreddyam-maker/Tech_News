import logging
from celery_app import celery_app, get_celery_session, run_in_worker_loop
from app.services.recovery.service import RecoveryService
from app.core.metrics.registry import REGISTRY

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.recovery.evaluate_system_health")
def evaluate_system_health_task():
    """
    Autonomous Recovery Engine heartbeat task.
    Pulls current system telemetry and evaluates recovery policies.
    """
    logger.info("Starting Autonomous Recovery Evaluation cycle.")

    async def _execute():
        # First, gather metrics from the health endpoints or Prometheus registry
        # For simplicity and isolation, we mock gathering the metrics using a direct dictionary 
        # (in production, we would extract these natively or call the same logic as the health checks)
        
        async with get_celery_session() as db:
            from sqlalchemy import select, func, text
            from app.models.article import ProcessedArticle, ArticleReadModel
            
            # 1. Gather CQRS Metrics
            processed_stmt = select(func.count(ProcessedArticle.id)).where(ProcessedArticle.published_status == "published")
            processed_count = (await db.execute(processed_stmt)).scalar() or 0
            read_stmt = select(func.count(ArticleReadModel.id))
            read_count = (await db.execute(read_stmt)).scalar() or 0
            projection_lag = abs(processed_count - read_count)
            
            cqrs_metrics = {
                "projection_lag": projection_lag
            }
            
            # 2. Gather Thumbnail Metrics (Mocked missing rate calculation)
            thumbnail_metrics = {
                "missing_rate": 0.0
            }
            
            # 3. Gather Queue Metrics (Mocked from Redis)
            queue_metrics = {
                "rss_queue_depth": 0,
                "projection_queue_depth": 0,
                "thumbnail_queue_depth": 0
            }

            # Run Evaluations
            service = RecoveryService(db)
            
            cqrs_decision = await service.evaluate_and_recover(service.cqrs_policy, cqrs_metrics)
            thumbnail_decision = await service.evaluate_and_recover(service.thumbnail_policy, thumbnail_metrics)
            queue_decision = await service.evaluate_and_recover(service.queue_policy, queue_metrics)
            
            return {
                "cqrs": cqrs_decision.approved,
                "thumbnail": thumbnail_decision.approved,
                "queue": queue_decision.approved
            }

    try:
        results = run_in_worker_loop(_execute())
        logger.info(f"Autonomous Recovery Evaluation complete. Triggered: {results}")
        return results
    except Exception as e:
        logger.error(f"Autonomous Recovery Evaluation failed: {e}")
        return {"status": "error"}
