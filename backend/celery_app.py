import logging
from typing import Any

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

# Pre-load all SQLAlchemy models to prevent registry mapper errors in worker tasks
from app.core.config import settings
from app.models.article import Category, RawArticle, ProcessedArticle, ArticleReadModel
from app.models.source import Source
from app.models.user import User, AIJobHistory, ArticleRevision, AuditLog, Notification, OAuthAccount, Permission, Role, RolePermission, UserSession
from app.models.workspace import Workspace, WorkspaceArticle, WorkspaceConversation, WorkspaceNote, WorkspaceNoteVersion, WorkspaceActivity, WorkspaceDigest
from app.models.editorial import PublicationRecord, EditorialDraft, EditorialDecision, DiscussionThread, DraftComment, DraftVersion, EditorialReviewArtifact, EditorialPatch, EditorialSession
from app.models.distribution import DistributionManifest, DistributionJob, DeliveryReport
from app.models.tnt_knowledge import ArticleEntityLink, EntityNode, ArticleTopicLink, TopicNode

logger = logging.getLogger("tech_news.celery")

# Core Celery Queue Initializer
celery_app = Celery(
    "tech_news_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.distribution_tasks",
        "app.tasks.editorial_tasks",
        "app.tasks.summary_tasks",
        "app.tasks.article_intelligence",
        "app.tasks.monitoring",
        "app.tasks.recovery_tasks",
        "app.tasks.root_cause_tasks",
        "app.tasks.telemetry_tasks",
    ]
)

# Standard worker configurations with robust queue routing and timeout bounds

import asyncio

from celery.signals import worker_process_init
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

celery_engine = None
CeleryAsyncSessionLocal = None
worker_loop = None

@worker_process_init.connect
def init_worker_process(**kwargs):
    global celery_engine, CeleryAsyncSessionLocal, worker_loop

    # Create persistent event loop for this worker process
    worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)

    # Initialize the engine bound to this worker's loop
    celery_engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
    )
    CeleryAsyncSessionLocal = sessionmaker(
        bind=celery_engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("Celery worker process initialized with process-local isolated async_engine and loop.")

def run_in_worker_loop(coro):
    """Helper to safely run coroutines using the persistent worker loop, or fallback to a new one."""
    global worker_loop
    if worker_loop and not worker_loop.is_closed():
        return worker_loop.run_until_complete(coro)
    else:
        # Fallback for sync execution contexts (e.g., tests or eager mode)
        return asyncio.run(coro)

def get_celery_session():
    """Returns the worker-local session maker, or global if not in a worker."""
    global CeleryAsyncSessionLocal
    if CeleryAsyncSessionLocal:
        return CeleryAsyncSessionLocal()
    return AsyncSessionLocal()

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Fail-fast request timeouts: prevent hung scraper or API tasks from blocking workers
    task_time_limit=300,  # Hard timeout (5 minutes)
    task_soft_time_limit=240,  # Soft timeout (4 minutes, raises SoftTimeLimitExceeded)
    # Queue Routing Topology
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default.#"),
        Queue("ingestion", routing_key="ingestion.#"),
        Queue("ai_processing", routing_key="ai_processing.#"),
        Queue("embedding_processing", routing_key="embedding_processing.#"),
        Queue("moderation", routing_key="moderation.#"),
    ),
    task_routes={
        "tasks.scrapers.run_all_sources": {"queue": "ingestion"},
        "tasks.scrapers.force_crawl_source": {"queue": "ingestion"},
        "tasks.ai.process_raw_article": {"queue": "ai_processing"},
        "tasks.ai.process_embedding_task": {"queue": "embedding_processing"},
        "tasks.admin.moderate_article": {"queue": "moderation"},
        "tasks.images.download_thumbnail": {"queue": "default"},
        "tasks.ranking.rebuild_news_rankings": {"queue": "default"},
        "tasks.editorial.log_editorial_decision_snapshot": {"queue": "default"},
        "run_article_intelligence_pipeline": {"queue": "ai_processing"},
    },

)

# Celery Beat Periodic Task Scheduler
celery_app.conf.beat_schedule = {
    "auto-rss-ingestion": {
        "task": "tasks.scrapers.run_all_sources",
        "schedule": 900.0,  # Every 15 minutes
        "options": {"queue": "ingestion"},
    },
    "auto-publish-scheduled-drafts": {
        "task": "check_and_publish_scheduled_drafts_task",
        "schedule": 60.0,
        "options": {"queue": "default"},
    },
    "process-event-outbox": {
        "task": "process_event_outbox_task",
        "schedule": 10.0,
        "options": {"queue": "default"},
    },
    "trend-prioritization-ai-queue": {
        "task": "tasks.scrapers.run_trend_prioritization_and_ai_queue_task",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"queue": "ingestion"},
    },
    "periodic-trends-calculation": {
        "task": "tasks.scrapers.run_trends_calculation_task",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"queue": "ingestion"},
    },
    "periodic-news-ranking-and-expiry": {
        "task": "tasks.ranking.rebuild_news_rankings",
        "schedule": 43200.0,  # Every 12 hours
        "options": {"queue": "default"},
    },
    "periodic-editorial-decision-snapshot": {
        "task": "tasks.editorial.log_editorial_decision_snapshot",
        "schedule": 3600.0,  # Every hour
        "options": {"queue": "default"},
    },
    "capture-story-telemetry-snapshots": {
        "task": "capture_story_telemetry_snapshots",
        "schedule": crontab(minute="0"),  # Every hour on the hour
        "options": {"queue": "default"},
    },

    "collect-queue-metrics": {
        "task": "tasks.monitoring.collect_queue_metrics",
        "schedule": 5.0,
        "options": {"queue": "default"},
    },
    "collect-infrastructure-metrics": {
        "task": "tasks.monitoring.collect_infrastructure_metrics",
        "schedule": 10.0,
        "options": {"queue": "default"},
    },
    "collect-overview-metrics": {
        "task": "tasks.monitoring.collect_overview_metrics",
        "schedule": 60.0,
        "options": {"queue": "default"},
    },
    "collect-ai-queue-metrics": {
        "task": "tasks.monitoring.collect_ai_queue_metrics",
        "schedule": 10.0,
        "options": {"queue": "default"},
    },
    "collect-ai-recovery-metrics": {
        "task": "tasks.monitoring.collect_ai_recovery_metrics",
        "schedule": 30.0,
        "options": {"queue": "default"},
    },
    "collect-ai-performance-metrics": {
        "task": "tasks.monitoring.collect_ai_performance_metrics",
        "schedule": 60.0,
        "options": {"queue": "default"},
    },
    "autonomous-recovery-evaluation": {
        "task": "tasks.recovery.evaluate_system_health",
        "schedule": 60.0, # Every minute
        "options": {"queue": "default"},
    },
    "nightly-backup": {
        "task": "tasks.backup.run_backup_task",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "default"},
    },
    "retention-cleanup": {
        "task": "tasks.backup.run_retention_task",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "default"},
    },
}

import os
import socket
import threading
import time

from celery.signals import beat_init


@beat_init.connect
def start_beat_heartbeat(sender, **kwargs):
    """
    Spawns a background daemon thread in the Celery Beat process
    to periodically write its true heartbeat to Redis.
    """

    def heartbeat_loop():
        from datetime import datetime, timezone

        import redis

        from app.core.config import settings

        # Use sync redis client since we're in a background thread
        try:
            r = redis.Redis.from_url(settings.REDIS_URL)
        except Exception as e:
            logger.error(f"Beat heartbeat thread failed to connect to Redis: {e}")
            return

        while True:
            try:
                payload = {
                    "service": "celery-beat",
                    "last_tick": datetime.now(timezone.utc).isoformat(),
                    "tick_interval": 10,
                    "heartbeat_age_ms": 0,
                    "scheduler_version": getattr(sender, "__version__", "unknown"),
                    "hostname": socket.gethostname(),
                    "pid": os.getpid(),
                }
                r.set("telemetry:v2:celery_beat_heartbeat", json.dumps(payload), ex=30)
            except Exception as e:
                logger.warning(f"Failed to update native celery_beat_heartbeat in Redis: {e}")

            time.sleep(10)

    t = threading.Thread(target=heartbeat_loop, daemon=True, name="BeatHeartbeatThread")
    t.start()
    logger.info("Celery Beat: Started native heartbeat daemon thread (10s interval).")


@celery_app.task(name="tasks.scrapers.run_all_sources")
def run_scheduled_scrapers_task():
    """
    Background worker cron-job task for scheduling scraper agent collection.
    """

    from app.services.ingestion.pipeline import run_source_ingestion_pipeline

    logger.info("Initializing automated scraping ingestion round...")

    async def _execute():
        async with get_celery_session() as db:
            return await run_source_ingestion_pipeline(db)


    metrics = run_in_worker_loop(_execute())
    logger.info(f"Automated scraping ingestion round complete. Metrics: {metrics}")

    # Proactively trigger trend prioritization and trends calculation immediately after crawl
    run_trend_prioritization_and_ai_queue_task.delay()
    run_trends_calculation_task.delay()

    return {"status": "success", "metrics": metrics}


@celery_app.task(name="tasks.scrapers.force_crawl_source")
def force_crawl_source_task(source_id: int):
    """
    Asynchronous Celery task for admin-triggered force crawl of a single source.
    Dispatched by the /admin/sources/{id}/trigger endpoint to avoid HTTP timeouts.
    """

    from app.services.ingestion.pipeline import crawl_single_source_pipeline

    logger.info(f"Force crawl task started for source ID: {source_id}")

    async def _execute():
        async with get_celery_session() as db:
            return await crawl_single_source_pipeline(db, source_id)


    metrics = run_in_worker_loop(_execute())
    logger.info(f"Force crawl task complete for source ID: {source_id}. Metrics: {metrics}")

    # Chain trend recalculation after crawl completes
    run_trend_prioritization_and_ai_queue_task.delay()

    return {"status": "success", "source_id": source_id, "metrics": metrics}


import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.models.source import Source


async def enqueue_fresh_articles(db) -> int:
    # Query all fetched articles
    stmt = (
        select(RawArticle, Source)
        .outerjoin(Source, RawArticle.source_id == Source.id)
        .where(RawArticle.status == "fetched")
        .order_by(RawArticle.scraped_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    if not rows:
        return 0

    # Group articles by source to enforce anti-spam cap
    source_groups = {}
    for raw_art, source_obj in rows:
        src_id = raw_art.source_id or -1
        if src_id not in source_groups:
            source_groups[src_id] = []
        source_groups[src_id].append((raw_art, source_obj))

    prioritized_articles = []

    # Enforce Source Cap: max 3 articles per source per prioritization cycle
    for src_id, art_list in source_groups.items():
        capped_list = art_list[:3]  # Freshest 3
        prioritized_articles.extend(capped_list)

    # Rank prioritized list: weight by source credibility
    prioritized_articles.sort(key=lambda x: x[1].credibility_score if x[1] else 50, reverse=True)

    # Select top 8 high-density stories to enqueue
    top_selection = prioritized_articles[:8]

    enqueued_count = 0
    for raw_art, _ in top_selection:
        # Mark as 'ai_queued' in database
        raw_art.status = "ai_queued"
        # Schedule task
        process_raw_article_task.delay(raw_art.id)
        enqueued_count += 1

    return enqueued_count


async def recover_stale_ai_jobs(db) -> tuple[int, int]:
    stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)

    # We use with_for_update(skip_locked=True) to prevent multiple workers from recovering the same rows
    stale_stmt = (
        select(RawArticle)
        .where(RawArticle.status == "ai_queued")
        .where(RawArticle.updated_at < stale_threshold)
        .order_by(RawArticle.updated_at.asc())
        .limit(8)
        .with_for_update(skip_locked=True)
    )
    stale_res = await db.execute(stale_stmt)
    stale_articles = stale_res.scalars().all()

    recovered_count = 0
    failed_count = 0

    for raw_art in stale_articles:
        if raw_art.retry_count >= 3:
            raw_art.status = "dead_letter"
            raw_art.dead_letter_reason = "Max retries exceeded during stale job recovery (ai_timeout)"
            raw_art.dead_letter_at = datetime.now(timezone.utc)
            raw_art.error_log = "ai_timeout"
            logger.error(
                f"Recovered stale ai_queued article id={raw_art.id} age=15m+ retry={raw_art.retry_count} -> DEAD_LETTER"
            )
            failed_count += 1
        else:
            raw_art.retry_count += 1
            raw_art.last_retry_at = datetime.now(timezone.utc)
            process_raw_article_task.delay(raw_art.id)
            logger.info(f"Recovered stale ai_queued article id={raw_art.id} age=15m+ retry={raw_art.retry_count}")
            recovered_count += 1

    return recovered_count, failed_count


@celery_app.task(name="tasks.scrapers.run_trend_prioritization_and_ai_queue_task")
def run_trend_prioritization_and_ai_queue_task():
    """
    Decoupled Trend Prioritization & Throttled AI Queuing Engine.
    Filters raw articles in 'fetched' state, applies anti-spam source caps (max 3/source),
    ranks by credibility, and enqueues top 8 articles for AI summarization.
    """

    async def _execute():
        async with get_celery_session() as db:
            fresh_enqueued = await enqueue_fresh_articles(db)
            recovered, failed = await recover_stale_ai_jobs(db)

            await db.commit()

            # Emit telemetry for Phase 4D
            try:
                redis_client = get_redis_client()
                if recovered > 0:
                    await redis_client.incrby("telemetry_recovered_ai_jobs", recovered)
                if failed > 0:
                    await redis_client.incrby("telemetry_failed_ai_jobs", failed)
            except Exception as e:
                logger.error(f"Failed to emit recovery telemetry: {e}")

            return fresh_enqueued, recovered, failed


    fresh, recovered, failed = run_in_worker_loop(_execute())
    logger.info(
        f"Prioritization and Throttling complete. Enqueued {fresh} articles for AI summarization. Recovered: {recovered}, Failed: {failed}"
    )
    return {"status": "success", "enqueued_count": fresh, "recovered_count": recovered, "failed_count": failed}


@celery_app.task(name="tasks.scrapers.run_trends_calculation_task")
def run_trends_calculation_task():
    """
    Background worker cron task to compute time-decay and authority-weighted trends.
    """

    from app.services.ingestion.trends import calculate_latest_trends

    async def _execute():
        async with get_celery_session() as db:
            return await calculate_latest_trends(db)


    metrics = run_in_worker_loop(_execute())
    logger.info(f"Trends calculation cycle complete. Metrics: {metrics}")
    return {"status": "success", "metrics": metrics}


@celery_app.task(name="tasks.ai.process_raw_article")
def process_raw_article_task(raw_id: int):
    """
    AI summarization and categorization parsing execution task.
    """

    from app.services.ingestion.pipeline import process_raw_article_to_editorial

    logger.info(f"Triggering asynchronous AI processing pipeline for raw article ID: {raw_id}")

    async def _execute():
        async with get_celery_session() as db:
            return await process_raw_article_to_editorial(db, raw_id)


    res = run_in_worker_loop(_execute())
    logger.info(f"AI processing pipeline complete for RawArticle ID: {raw_id}. Result: {res}")
    return res


@celery_app.task(name="tasks.ai.process_embedding_task", bind=True, max_retries=5, default_retry_delay=60)
def process_embedding_task(self, article_id: int):
    """
    Asynchronous task to generate vector embeddings for processed articles.
    """

    from app.ai.embedding import EmbeddingService

    logger.info(f"Triggering asynchronous embedding generation for ProcessedArticle ID: {article_id}")

    async def _execute():
        async with get_celery_session() as db:
            service = EmbeddingService()
            return await service.process_article_embedding(db, article_id)


    try:
        res = run_in_worker_loop(_execute())
        logger.info(f"Embedding generation complete for ProcessedArticle ID: {article_id}. Result: {res}")
        return res
    except Exception as exc:
        logger.error(f"Embedding generation failed for ProcessedArticle ID: {article_id}. Error: {exc}")
        # Use exponential backoff for retries: 60s, 120s, 240s, etc.
        retry_delay = self.default_retry_delay * (2**self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)


@celery_app.task(name="tasks.images.download_thumbnail")
def download_thumbnail_task(article_id: int, candidates: list):
    """
    Asynchronous task to download, validate, and save article thumbnails.
    Handles structured candidates list, calculates perceptual hashes (pHash),
    performs duplicate detection (Hamming distance <= 5) against the last 50 processed articles,
    and falls back to a backend cyberpunk banner if all candidates fail.
    """

    from sqlalchemy import select

    from app.core.event_bus import publish_event

    logger.info(f"Triggering asynchronous image download for ProcessedArticle ID: {article_id}")

    async def _execute():
        from app.services.ingestion.image_helper import download_and_validate_in_memory, save_image_to_disk
        async with get_celery_session() as db:
            # from app.models.telemetry import ThumbnailDecisionLog

            # Query the last 50 processed articles' thumbnail hashes
            hash_stmt = (
                select(ProcessedArticle.thumbnail_hash)
                .where(
                    (ProcessedArticle.thumbnail_hash != None)
                    & (ProcessedArticle.thumbnail_hash != "fallback")
                    & (ProcessedArticle.thumbnail_status == "downloaded")
                )
                .order_by(ProcessedArticle.created_at.desc())
                .limit(50)
            )
            hash_res = await db.execute(hash_stmt)
            last_hashes = [row for row in hash_res.scalars().all() if row]

            # Fetch last 4 passes to guard against consecutive fallbacks
            pass_stmt = (
                select(ProcessedArticle.winner_pass)
                .where(ProcessedArticle.winner_pass != None)
                .order_by(ProcessedArticle.created_at.desc())
                .limit(4)
            )
            pass_res = await db.execute(pass_stmt)
            recent_passes = [r for r in pass_res.scalars().all() if r]
            fallback_in_last_4 = "fallback" in recent_passes

            candidate_count = len(candidates) if candidates else 0
            decision_logs = []
            valid_candidates = []

            # Ensure candidates are dictionaries
            normalized_candidates = []
            if candidates:
                for cand in candidates:
                    if isinstance(cand, dict):
                        normalized_candidates.append(cand)
                    else:
                        normalized_candidates.append({"url": cand, "source": "og:image", "score": 0})

            # Map validation errors to target formats
            REASON_MAP = {
                "dimension_filter": "too_small",
                "aspect_ratio_filter": "aspect_ratio",
                "invalid_content_type": "bad_mime",
                "keyword_penalty": "blacklisted_filename",
                "download_failure": "download_failure",
                "http_403": "http_403",
                "http_404": "http_404",
                "http_405": "http_405",
                "network_timeout": "network_timeout",
                "connection_error": "connection_error",
                "ssl_failure": "ssl_failure",
                "decode_failed": "decode_failed",
            }

            from app.services.ingestion.image_helper import calculate_quality_score

            # Phase 1: Try strict pass
            for cand in normalized_candidates:
                url = cand["url"]
                source = cand["source"]
                bypass = source in ("og:image", "twitter:image")

                res = await download_and_validate_in_memory(url, relaxed=False, bypass_blacklist=bypass)
                if not res:
                    valid_candidates.append({
                        "candidate": cand,
                        "valid": False,
                        "reason": "decode_failed",
                        "dims": None,
                        "img": None,
                        "phash": None,
                        "relaxed": False,
                    })
                    continue

                img, phash_str, rejection_reason, dims = res
                if rejection_reason:
                    mapped_reason = REASON_MAP.get(rejection_reason, rejection_reason)
                    valid_candidates.append({
                        "candidate": cand,
                        "valid": False,
                        "reason": mapped_reason,
                        "dims": dims,
                        "img": None,
                        "phash": None,
                        "relaxed": False,
                    })
                else:
                    valid_candidates.append({
                        "candidate": cand,
                        "valid": True,
                        "reason": None,
                        "dims": dims,
                        "img": img,
                        "phash": phash_str,
                        "relaxed": False,
                    })

            # Check if we have any valid candidate in strict pass
            has_strict_valid = any(c["valid"] for c in valid_candidates)

            # Phase 2: If no strict valid candidate, try relaxed pass
            if not has_strict_valid:
                valid_candidates = []
                for cand in normalized_candidates:
                    url = cand["url"]
                    source = cand["source"]
                    bypass = source in ("og:image", "twitter:image")

                    res = await download_and_validate_in_memory(url, relaxed=True, bypass_blacklist=bypass)
                    if not res:
                        valid_candidates.append({
                            "candidate": cand,
                            "valid": False,
                            "reason": "decode_failed",
                            "dims": None,
                            "img": None,
                            "phash": None,
                            "relaxed": True,
                        })
                        continue

                    img, phash_str, rejection_reason, dims = res
                    if rejection_reason:
                        mapped_reason = REASON_MAP.get(rejection_reason, rejection_reason)
                        valid_candidates.append({
                            "candidate": cand,
                            "valid": False,
                            "reason": mapped_reason,
                            "dims": dims,
                            "img": None,
                            "phash": None,
                            "relaxed": True,
                        })
                    else:
                        valid_candidates.append({
                            "candidate": cand,
                            "valid": True,
                            "reason": None,
                            "dims": dims,
                            "img": img,
                            "phash": phash_str,
                            "relaxed": True,
                        })

            # Calculate composite scores for all valid candidates
            scored_candidates = []
            for item in valid_candidates:
                if item["valid"]:
                    cand = item["candidate"]
                    img = item["img"]
                    dims = item["dims"]
                    img_format = img.format.lower() if img.format else "webp"
                    score = calculate_quality_score(cand, dims, img_format)
                    item["score"] = score
                    scored_candidates.append(item)
                else:
                    item["score"] = -9999

            winner: Any = None
            winner_score = -9999
            winner_pass = None
            winner_save_res = None

            # Find the highest scoring candidate
            # Tie-breaker: stable traversal of scored_candidates (which follows candidates order)
            for item in scored_candidates:
                if item["score"] > winner_score:
                    winner_score = item["score"]
                    winner = item

            thumb_res = None
            if winner:
                save_res = save_image_to_disk(winner["img"], article_id, winner["phash"])
                if save_res:
                    winner_save_res = save_res
                    winner_pass = "relaxed" if winner["relaxed"] else "strict"
                    thumb_res = {
                        "thumbnail_url": winner["candidate"]["url"],
                        "thumbnail_local": save_res["thumbnail_local"],
                        "thumbnail_hash": winner["phash"],
                        "thumbnail_source": winner["candidate"]["source"],
                    }

            if not thumb_res:
                from app.models.article import ThumbnailFailureReason
                
                failure_reason = ThumbnailFailureReason.UNKNOWN
                if candidate_count == 0:
                    failure_reason = ThumbnailFailureReason.NO_IMAGES_FOUND
                else:
                    reasons = [c["reason"] for c in valid_candidates if c["reason"]]
                    if "http_404" in reasons:
                        failure_reason = ThumbnailFailureReason.NO_IMAGES_FOUND
                    elif "http_403" in reasons:
                        failure_reason = ThumbnailFailureReason.BOT_BLOCKED
                    elif "network_timeout" in reasons or "connection_error" in reasons:
                        failure_reason = ThumbnailFailureReason.DOWNLOAD_TIMEOUT
                    else:
                        failure_reason = ThumbnailFailureReason.PIPELINE_FAILURE
                
                allowed_ai_reasons = {
                    ThumbnailFailureReason.NO_IMAGES_FOUND,
                    ThumbnailFailureReason.HOTLINK_PROTECTION,
                    ThumbnailFailureReason.BOT_BLOCKED,
                    ThumbnailFailureReason.ACCESS_DENIED,
                    ThumbnailFailureReason.SOURCE_RESTRICTED,
                }
                
                ai_generated = False
                if failure_reason in allowed_ai_reasons:
                    from app.services.ingestion.thumbnail_specification import GeminiThumbnailSpecificationProvider
                    from app.services.ingestion.thumbnail_generator import ThumbnailImageService
                    import asyncio
                    from sqlalchemy.orm import selectinload
                    
                    art_stmt = select(ProcessedArticle).options(selectinload(ProcessedArticle.category)).where(ProcessedArticle.id == article_id)
                    art_row = await db.execute(art_stmt)
                    art_record = art_row.scalar_one_or_none()
                    
                    if art_record:
                        spec_gen = GeminiThumbnailSpecificationProvider()
                        cat_name = art_record.category.name if art_record.category else ""
                        spec_res = await spec_gen.generate_specification(
                            title=art_record.title,
                            summary=art_record.summary,
                            category=cat_name,
                            source=art_record.source
                        )
                        
                        if spec_res.get("status") == "success" and spec_res.get("confidence", 0) >= 0.85 and spec_res.get("spec"):
                            img_service = ThumbnailImageService()
                            img_res = await img_service.generate(spec_res["spec"])
                            
                            if img_res:
                                import uuid
                                ai_phash = "ai_" + uuid.uuid4().hex[:8]
                                
                                import io
                                from PIL import Image
                                ai_img = Image.open(io.BytesIO(img_res.image_bytes))
                                
                                ai_save_res = save_image_to_disk(ai_img, article_id, ai_phash)
                                if ai_save_res:
                                    thumb_res = {
                                        "thumbnail_url": ai_save_res["thumbnail_local"],
                                        "thumbnail_local": ai_save_res["thumbnail_local"],
                                        "thumbnail_hash": ai_phash,
                                        "thumbnail_source": f"ai_generated_{img_res.provider_name}",
                                        "thumbnail_type": "AI_GENERATED",
                                        "thumbnail_generation_reason": failure_reason.value
                                    }
                                    winner_pass = "ai_recovery"
                                    winner_score = 100
                                    ai_generated = True
                                    
                                    from app.models.article import AIThumbnailMetadata
                                    ai_meta = AIThumbnailMetadata(
                                        article_id=article_id,
                                        headline=spec_res["spec"].get("headline", art_record.title),
                                        summary=art_record.summary,
                                        entities_json=spec_res["spec"].get("entities", []),
                                        prompt_used=spec_res["spec"].get("topic", "") + " " + ", ".join(spec_res["spec"].get("visual_elements", [])),
                                        model_name=img_res.provider_name,
                                        model_version=img_res.model_version,
                                        generation_duration_ms=img_res.duration_ms,
                                        confidence=spec_res["confidence"]
                                    )
                                    db.add(ai_meta)
                                    
                                    from app.core.event_bus import publish_event
                                    await publish_event("INGESTION", "AI Thumbnail Generated", "info", {
                                        "article_id": article_id,
                                        "thumbnail_url": thumb_res["thumbnail_url"],
                                        "model_used": img_res.provider_name,
                                        "duration_ms": img_res.duration_ms,
                                        "confidence": spec_res["confidence"]
                                    })
                            else:
                                from app.core.event_bus import publish_event
                                await publish_event("INGESTION", "AI Thumbnail Generation Failed", "error", {
                                    "article_id": article_id,
                                    "error_type": "IMAGE_GENERATION_FAILED",
                                    "reason": "All image generators failed to return an image"
                                })
                        elif spec_res.get("status") == "error":
                            error_type = spec_res.get("error_type", "UNKNOWN_ERROR")
                            if error_type == "PROVIDER_UNAVAILABLE":
                                from app.core.metrics.ai_thumbnails import tnt_ai_thumbnail_provider_unavailable_total
                                tnt_ai_thumbnail_provider_unavailable_total.labels(provider_name="gemini").inc()
                                
                            from app.core.event_bus import publish_event
                            await publish_event("INGESTION", "AI Thumbnail Generation Failed", "error", {
                                "article_id": article_id,
                                "error_type": error_type,
                                "reason": spec_res.get("reason", "Unknown error occurred")
                            })
                        else:
                            # It was rejected semantically (LOW_CONFIDENCE, Forbidden category, etc.)
                            from app.core.event_bus import publish_event
                            await publish_event("INGESTION", "AI Thumbnail Rejected", "warning", {
                                "article_id": article_id,
                                "confidence": spec_res.get("confidence", 0.0),
                                "reason": spec_res.get("reason", "Low Confidence or Forbidden")
                            })

                if not ai_generated:
                    thumb_res = {
                        "thumbnail_url": "/images/fallback-news.webp",
                        "thumbnail_local": "/images/fallback-news.webp",
                        "thumbnail_hash": "fallback",
                        "thumbnail_source": "fallback",
                        "thumbnail_type": "FALLBACK",
                        "thumbnail_generation_reason": failure_reason.value if 'failure_reason' in locals() else "UNKNOWN"
                    }
                    winner_pass = "fallback"
                    winner_score = 0
                    logger.warning(f"Image Task: Assigning fallback banner for article ID {article_id}. Reason: {thumb_res.get('thumbnail_generation_reason')}")

            # Log all evaluated candidates
            for item in valid_candidates:
                cand: Any = item["candidate"]
                url = cand["url"]
                source = cand["source"]
                dims = item["dims"]

                is_winner = (winner and winner["candidate"]["url"] == url and winner_save_res is not None)
                accepted = is_winner

                if accepted:
                    status_str = "winner"
                    reason_str = None
                    score_val = winner_score
                elif item["valid"]:
                    status_str = "rejected"
                    reason_str = "lower_score"
                    score_val = item["score"]
                else:
                    status_str = "rejected"
                    reason_str = item["reason"]
                    score_val = 0

                pass # Removed ThumbnailDecisionLog

            from app.services.ingestion.thumbnail_service import ThumbnailUpdatedApplicationService

            art = await ThumbnailUpdatedApplicationService.finalize_thumbnail_update(
                db=db,
                article_id=article_id,
                thumbnail_url=thumb_res["thumbnail_url"],
                thumbnail_local=thumb_res["thumbnail_local"],
                thumbnail_hash=thumb_res["thumbnail_hash"],
                thumbnail_source=thumb_res["thumbnail_source"],
                candidate_count=candidate_count,
                winner_pass=winner_pass,
                thumbnail_score=winner_score,
                thumbnail_type=thumb_res.get("thumbnail_type", "REAL_IMAGE"),
                thumbnail_generation_reason=thumb_res.get("thumbnail_generation_reason")
            )

            if art:
                art.thumbnail_score = winner_score
                art.thumbnail_algorithm_version = "v1"

                # for log in decision_logs:
                #     db.add(log)
                await db.commit()

                # Emit dynamic SSE real-time event to refresh thumbnail state in UI
                try:
                    await publish_event(
                        "INGESTION",
                        f"Article thumbnail updated: {art.title}",
                        "success",
                        {
                            "id": art.id,
                            "thumbnail_local": art.thumbnail_local,
                            "thumbnail_url": art.thumbnail_url,
                            "thumbnail_status": art.thumbnail_status,
                            "thumbnail_source": art.thumbnail_source,
                        },
                    )
                except Exception as sse_err:
                    logger.warning(f"Failed to publish SSE thumbnail update: {sse_err}")

            return {"status": "success", "downloaded": thumb_res["thumbnail_source"] != "fallback", "pass": winner_pass}


    res = run_in_worker_loop(_execute())
    return res


@celery_app.task(name="tasks.ranking.rebuild_news_rankings")
def rebuild_news_rankings_task():
    """
    12-Hour News Ranking Engine Task.
    Calculates impact, freshness, engagement and final scores, expires old articles,
    and rebuilds pre-ranked homepage feeds.
    """


    from app.services.ranking.news_ranking_engine import rank_articles

    async def _execute():
        async with get_celery_session() as db:
            return await rank_articles(db)


    metrics = run_in_worker_loop(_execute())
    logger.info(f"News Ranking Cycle complete. Metrics: {metrics}")

    # Proactively recalculate trends immediately after re-ranking
    run_trends_calculation_task.delay()

    return {"status": "success", "metrics": metrics}


@celery_app.task(name="tasks.editorial.log_editorial_decision_snapshot")
def log_editorial_decision_snapshot_task():
    """
    Hourly snapshot task to build the homepage and log the selection decisions
    to the EditorialDecisionLog table in database.
    """
    from app.editorial.homepage_builder import HomepageBuilder

    async def _execute():
        async with get_celery_session() as db:
            await HomepageBuilder.build_homepage(db, log_decisions=True)

    run_in_worker_loop(_execute())
    logger.info("Hourly editorial decision log snapshot complete.")
    return {"status": "success"}



from celery.signals import task_postrun


@task_postrun.connect
def on_task_postrun(sender=None, task_id=None, task=None, **kwargs):
    """
    Hook executing after every Celery task run. Records completion timestamps
    to Redis to measure processing rates dynamically.
    """
    try:
        import time

        import redis

        from app.core.config import settings

        r = redis.Redis.from_url(settings.REDIS_URL)
        now = time.time()
        # Add task execution to a sorted set
        r.zadd("completed_tasks_timestamps", {task_id: now})
        # Keep only the last 10 minutes of completions to keep the set small
        r.zremrangebyscore("completed_tasks_timestamps", "-inf", now - 600)
    except Exception as e:
        logger.warning(f"Failed to record completed task in Redis: {e}")

# Import editorial tasks to register them


@celery_app.task(name="tasks.monitoring.collect_queue_metrics")
def collect_queue_metrics_task():


    from app.services.monitoring.observability import run_queue_health_checks

    run_in_worker_loop(run_queue_health_checks())
    return {"status": "success"}


@celery_app.task(name="tasks.monitoring.collect_infrastructure_metrics")
def collect_infrastructure_metrics_task():


    from app.services.monitoring.observability import run_infrastructure_health_checks

    run_in_worker_loop(run_infrastructure_health_checks())
    return {"status": "success"}


@celery_app.task(name="tasks.monitoring.collect_overview_metrics")
def collect_overview_metrics_task():


    from app.services.monitoring.observability import run_overview_health_checks

    run_in_worker_loop(run_overview_health_checks())
    return {"status": "success"}


@celery_app.task(name="tasks.behavioral.update_user_interest_profile")
def update_user_interest_profile_task(user_id: int | None = None, anonymous_id: str | None = None):
    """
    Asynchronous task to run the ProfileUpdater and compute UserInterest rows.
    Triggered when a ReadingSession reaches a completion milestone.
    """

    from app.services.behavioral.profiler import ProfileUpdater

    logger.info(f"Triggering InterestProfiler for user_id={user_id}, anonymous_id={anonymous_id}")

    async def _execute():
        async with get_celery_session() as db:
            updater = ProfileUpdater(db)
            await updater.update_profile_for_user(user_id=user_id, anonymous_id=anonymous_id)


    res = run_in_worker_loop(_execute())
    logger.info(f"InterestProfiler complete for user_id={user_id}, anonymous_id={anonymous_id}")
    return res


@celery_app.task(name="tasks.backup.run_backup_task")
def run_backup_task():
    """
    Automated backup task triggered daily at 02:00 UTC.
    """


    from app.backup.service import create_backup


    backup_id = run_in_worker_loop(create_backup())
    logger.info(f"Scheduled backup completed successfully: {backup_id}")
    return {"status": "success", "backup_id": backup_id}


@celery_app.task(name="tasks.backup.run_retention_task")
def run_retention_task():
    """
    Automated retention cleanup task triggered daily at 03:00 UTC.
    """

    from app.backup.retention import get_gfs_retention
    from app.backup.storage import get_storage

    logger.info("Starting scheduled backup retention evaluation...")
    storage = get_storage()
    backup_ids = storage.list_backups()
    keep, delete = get_gfs_retention(backup_ids)

    deleted_count = 0
    for bid in delete:
        logger.info(f"Retention policy match: deleting expired backup: {bid}")
        storage.delete_backup(bid)
        deleted_count += 1

    logger.info(f"Backup retention cleanup complete. Kept: {len(keep)}, Deleted: {deleted_count}")
    return {"status": "success", "kept": keep, "deleted": delete}


@celery_app.task(name="tasks.monitoring.collect_ai_queue_metrics")
def collect_ai_queue_metrics_task():


    from app.services.monitoring.observability import collect_ai_queue_metrics

    run_in_worker_loop(collect_ai_queue_metrics())
    return {"status": "success"}


@celery_app.task(name="tasks.monitoring.collect_ai_recovery_metrics")
def collect_ai_recovery_metrics_task():


    from app.services.monitoring.observability import collect_ai_recovery_metrics

    run_in_worker_loop(collect_ai_recovery_metrics())
    return {"status": "success"}


@celery_app.task(name="tasks.monitoring.collect_ai_performance_metrics")
def collect_ai_performance_metrics_task():


    from app.services.monitoring.observability import collect_ai_performance_metrics

    run_in_worker_loop(collect_ai_performance_metrics())
    return {"status": "success"}
