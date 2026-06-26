import json
import logging
import socket
import time
from datetime import datetime, timedelta, timezone

from app.core.async_utils import run_async_task
from app.core.redis import get_redis_client
from app.services.monitoring.observability import (
    collect_ai_performance_metrics,
    collect_ai_queue_metrics,
    collect_ai_recovery_metrics,
    run_infrastructure_health_checks,
    run_overview_health_checks,
    run_queue_health_checks,
)
from celery_app import celery_app

logger = logging.getLogger("tech_news.tasks.monitoring")


def track_execution(task_name: str):
    """
    Decorator that records heartbeat execution metadata to Redis AND executes the atomic pipeline.
    """

    def decorator(async_func):
        async def wrapper(*args, **kwargs):
            started_at = datetime.now(timezone.utc)
            start_time = time.perf_counter()
            status = "running"
            error = None

            client = get_redis_client()
            pipe = client.pipeline(transaction=True)

            try:
                # Pass the pipe to the observability function so it can queue its telemetry writes
                result = await async_func(*args, pipe=pipe, **kwargs)
                status = "completed"
                return result
            except Exception as e:
                status = "failed"
                error = str(e)
                logger.error(f"Task {task_name} failed: {e}", exc_info=True)
                raise
            finally:
                completed_at = datetime.now(timezone.utc)
                duration_ms = (time.perf_counter() - start_time) * 1000.0

                # Check for slow collectors
                thresholds = {
                    "overview": 1000,
                    "queue": 300,
                    "infrastructure": 5000,
                    "ai_queue": 500,
                    "ai_recovery": 1000,
                    "ai_performance": 5000,
                }

                t_key = next((k for k in thresholds if k in task_name), "default")
                threshold = thresholds.get(t_key, 2000)

                if duration_ms > threshold:
                    logger.warning(f"Slow collector [{task_name}]: took {duration_ms:.2f}ms (threshold: {threshold}ms)")

                now_utc = datetime.now(timezone.utc)
                heartbeat_data = {
                    "task_name": task_name,
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "duration_ms": duration_ms,
                    "status": status,
                    "error": error,
                    "_meta": {
                        "schema_version": 2,
                        "collector_version": "2.0",
                        "build": "7.10",
                        "git_sha": "rc1_certified",
                        "generated_at": now_utc.isoformat(),
                        "expires_at": (now_utc + timedelta(seconds=300)).isoformat(),
                        "hostname": socket.gethostname(),
                    },
                }
                pipe.set(f"telemetry:v2:heartbeat:{task_name}", json.dumps(heartbeat_data), ex=300)

                try:
                    await pipe.execute()
                except Exception as e:
                    logger.error(f"Failed to execute atomic telemetry transaction for {task_name}: {e}")

        return wrapper

    return decorator


@celery_app.task(name="tasks.monitoring.collect_infrastructure_metrics")
def collect_infrastructure_metrics_task():
    logger.info("Starting collect_infrastructure_metrics_task")
    run_async_task(
        track_execution("tasks.monitoring.collect_infrastructure_metrics")(run_infrastructure_health_checks)()
    )


@celery_app.task(name="tasks.monitoring.collect_queue_metrics")
def collect_queue_metrics_task():
    logger.info("Starting collect_queue_metrics_task")
    run_async_task(track_execution("tasks.monitoring.collect_queue_metrics")(run_queue_health_checks)())


@celery_app.task(name="tasks.monitoring.collect_overview_metrics")
def collect_overview_metrics_task():
    logger.info("Starting collect_overview_metrics_task")
    run_async_task(track_execution("tasks.monitoring.collect_overview_metrics")(run_overview_health_checks)())


@celery_app.task(name="tasks.monitoring.collect_ai_queue_metrics")
def collect_ai_queue_metrics_task():
    logger.info("Starting collect_ai_queue_metrics_task")
    run_async_task(track_execution("tasks.monitoring.collect_ai_queue_metrics")(collect_ai_queue_metrics)())


@celery_app.task(name="tasks.monitoring.collect_ai_performance_metrics")
def collect_ai_performance_metrics_task():
    logger.info("Starting collect_ai_performance_metrics_task")
    run_async_task(track_execution("tasks.monitoring.collect_ai_performance_metrics")(collect_ai_performance_metrics)())


@celery_app.task(name="tasks.monitoring.collect_ai_recovery_metrics")
def collect_ai_recovery_metrics_task():
    logger.info("Starting collect_ai_recovery_metrics_task")
    run_async_task(track_execution("tasks.monitoring.collect_ai_recovery_metrics")(collect_ai_recovery_metrics)())
