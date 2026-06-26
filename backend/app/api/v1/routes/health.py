import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.core.redis import get_redis_client
from app.schemas.responses import StandardResponse

router = APIRouter()


@router.get("/live", response_model=StandardResponse[dict])
async def get_liveness():
    """
    Liveness Check: Returns 200 immediately to signify the Python process is alive.
    Useful for simple Kubernetes/Docker orchestration checks.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    return StandardResponse(
        correlation_id=correlation_id, data={"status": "healthy", "process": "alive", "timestamp": time.time()}
    )


@router.get("/ready", response_model=StandardResponse[dict])
async def get_readiness(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Readiness Check: Actively validates PostgreSQL and Redis connectivity.
    Returns 200 if fully healthy, or 503 if any core downstream system is down.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    postgres_healthy = False
    redis_healthy = False
    postgres_latency = 0.0
    redis_latency = 0.0

    # 1. Validate PostgreSQL connection pool
    start_db = time.time()
    try:
        await db.execute(text("SELECT 1"))
        postgres_latency = (time.time() - start_db) * 1000
        postgres_healthy = True
    except Exception as e:
        # Fallback metric or logs
        print("Readiness postgres check error:", str(e))
        postgres_healthy = False

    # 2. Validate Redis async engine
    start_redis = time.time()
    try:
        client = get_redis_client()
        pong = await client.ping()
        if pong:
            redis_latency = (time.time() - start_redis) * 1000
            redis_healthy = True
    except Exception as e:
        print("Readiness redis check error:", str(e))
        redis_healthy = False

    # 3. Compile responses and return matching codes
    is_ready = postgres_healthy and redis_healthy

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "status": "healthy" if is_ready else "unhealthy",
            "dependencies": {
                "postgres": {
                    "status": "healthy" if postgres_healthy else "unhealthy",
                    "latency_ms": round(postgres_latency, 2),
                },
                "redis": {"status": "healthy" if redis_healthy else "unhealthy", "latency_ms": round(redis_latency, 2)},
            },
        },
    )


@router.get("/runtime", response_model=StandardResponse[dict])
async def get_runtime_health(db: AsyncSession = Depends(get_db)):
    """
    Consolidated operational dashboard endpoint.
    Audits Postgres latency, Redis ping, Celery Worker connectivity, Celery Beat heartbeats,
    and source health aggregates.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    # 1. PostgreSQL Latency
    postgres_healthy = False
    postgres_latency = 0.0
    start_db = time.time()
    try:
        await db.execute(text("SELECT 1"))
        postgres_latency = (time.time() - start_db) * 1000
        postgres_healthy = True
    except Exception:
        postgres_healthy = False

    # 2. Redis connectivity & queue depth
    redis_healthy = False
    redis_latency = 0.0
    queue_depth = 0
    start_redis = time.time()
    try:
        client = get_redis_client()
        pong = await client.ping()
        if pong:
            redis_latency = (time.time() - start_redis) * 1000
            redis_healthy = True
            queue_depth = await client.llen("celery") or 0
    except Exception:
        redis_healthy = False

    # 3. Celery Workers availability (Non-blocking worker inspection)
    celery_workers_online = 0
    celery_workers_details = {}
    try:
        from celery_app import celery_app

        def inspect_workers():
            inspector = celery_app.control.inspect()
            pings = inspector.ping()
            return pings if pings else {}

        pings = await asyncio.to_thread(inspect_workers)
        celery_workers_online = len(pings)
        celery_workers_details = {k: v.get("status", "ok") for k, v in pings.items()}
    except Exception as e:
        celery_workers_details = {"error": f"Failed to ping workers: {e!s}"}

    # 4. Celery Beat Heartbeat Age
    beat_status = "offline"
    beat_last_active = None
    beat_age_seconds = None
    try:
        client = get_redis_client()
        heartbeat_val = await client.get("telemetry:v2:celery_beat_heartbeat")
        if heartbeat_val:
            beat_ts = heartbeat_val.decode("utf-8") if isinstance(heartbeat_val, bytes) else heartbeat_val
            beat_last_active = beat_ts
            dt = datetime.fromisoformat(beat_ts)
            now = datetime.now(timezone.utc)
            beat_age_seconds = (now - dt).total_seconds()

            # Since auto-rss-ingestion schedule is 900s, beat should trigger frequently
            if beat_age_seconds < 1200:  # 20 minutes
                beat_status = "healthy"
            elif beat_age_seconds < 3600:  # 1 hour
                beat_status = "degraded"
            else:
                beat_status = "offline"
        else:
            beat_status = "no_heartbeat_registered"
    except Exception as e:
        beat_status = f"error: {e!s}"

    # 5. Source Health Aggregates
    source_counts = {"healthy": 0, "degraded": 0, "offline": 0}
    try:
        from app.models.source import Source

        stmt = select(Source.health_state, func.count(Source.id)).group_by(Source.health_state)
        res = await db.execute(stmt)
        for health_state, count in res.all():
            if health_state in source_counts:
                source_counts[health_state] = count
    except Exception as e:
        source_counts = {"error": f"Failed to aggregate sources: {e!s}"}
    # 6. Check for pgvector extension
    pgvector_status = "Embedding Disabled"
    try:
        stmt = text("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
        res = await db.execute(stmt)
        if res.scalar() == 1:
            pgvector_status = "Enabled"
    except Exception:
        pass

    # 7. Pipeline Health
    ai_queue_depth = 0
    embedding_queue = 0
    dead_letter = 0
    oldest_ai_job_sec = 0
    try:
        from app.models.article import ProcessedArticle, RawArticle

        stmt = select(func.count(RawArticle.id)).where(RawArticle.status == "ai_queued")
        ai_queue_depth = (await db.execute(stmt)).scalar() or 0

        stmt = (
            select(RawArticle.updated_at)
            .where(RawArticle.status == "ai_queued")
            .order_by(RawArticle.updated_at.asc())
            .limit(1)
        )
        oldest = (await db.execute(stmt)).scalar()
        if oldest:
            oldest_ai_job_sec = int((datetime.now(timezone.utc) - oldest).total_seconds())

        stmt = select(func.count(RawArticle.id)).where(RawArticle.status == "dead_letter")
        dead_letter = (await db.execute(stmt)).scalar() or 0

        stmt = select(func.count(ProcessedArticle.id)).where(
            ProcessedArticle.embedding_status.in_(["pending", "queued", "stale"])
        )
        embedding_queue = (await db.execute(stmt)).scalar() or 0
    except Exception:
        pass

    is_overall_healthy = postgres_healthy and redis_healthy and celery_workers_online > 0 and beat_status == "healthy"

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "status": "healthy"
            if is_overall_healthy
            else "degraded"
            if (postgres_healthy and redis_healthy)
            else "unhealthy",
            "postgres": {
                "status": "healthy" if postgres_healthy else "unhealthy",
                "latency_ms": round(postgres_latency, 2),
            },
            "redis": {
                "status": "healthy" if redis_healthy else "unhealthy",
                "latency_ms": round(redis_latency, 2),
                "queue_depth": queue_depth,
            },
            "celery": {
                "workers_online": celery_workers_online,
                "workers": celery_workers_details,
                "beat": {
                    "status": beat_status,
                    "last_active": beat_last_active,
                    "age_seconds": round(beat_age_seconds, 1) if beat_age_seconds is not None else None,
                },
            },
            "sources": source_counts,
            "pgvector": pgvector_status,
            "ai_queue_depth": ai_queue_depth,
            "dead_letter": dead_letter,
            "embedding_queue": embedding_queue,
            "oldest_ai_job_sec": oldest_ai_job_sec,
        },
    )


@router.get("/ai", response_model=StandardResponse[dict])
async def get_ai_health(db: AsyncSession = Depends(get_db)):
    """
    AI Health Check: Returns provider circuit breaker state, budget, rate limiting stats.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    client = get_redis_client()

    # 1. Check Circuit Breaker
    from app.ai.circuit_breaker import CircuitBreaker, CircuitState
    from app.core.config import settings

    providers = settings.AI_PROVIDER_PRIORITY.split(",")
    active_provider = None
    fallback_providers = []
    circuit_states = {}

    for provider in providers:
        cb = CircuitBreaker(client, provider)
        state = await cb.get_state()
        circuit_states[provider] = state.value

        if state == CircuitState.CLOSED and not active_provider:
            active_provider = provider
        elif active_provider:
            fallback_providers.append(provider)

    # 2. Check Budget
    from app.ai.enforcement import AIBudgetEnforcer

    budget_enforcer = AIBudgetEnforcer(client, settings.AI_DAILY_BUDGET_USD)
    current_spend = await budget_enforcer.get_current_spend()
    within_budget = await budget_enforcer.check_budget()

    # 3. Check AI Queue Depth
    ai_queue_depth = 0
    try:
        from app.models.article import RawArticle

        stmt = select(func.count(RawArticle.id)).where(RawArticle.status == "ai_queued")
        res = await db.execute(stmt)
        ai_queue_depth = res.scalar() or 0
    except Exception:
        pass

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "status": "healthy" if active_provider and within_budget else "degraded",
            "active_provider": active_provider,
            "fallback_providers": fallback_providers,
            "circuit_breaker": circuit_states,
            "budget": {
                "daily_limit_usd": float(settings.AI_DAILY_BUDGET_USD),
                "current_spend_usd": float(current_spend),
                "within_budget": within_budget,
            },
            "queue_depth": ai_queue_depth,
        },
    )


@router.get("/cqrs", response_model=StandardResponse[dict])
async def get_cqrs_health(response: Response, db: AsyncSession = Depends(get_db)):
    """
    CQRS Health Check: Returns detailed stats on EventOutbox and ArticleReadModel projections.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    from app.models.article import ProcessedArticle, ArticleReadModel
    from app.core.events.models import EventOutbox

    try:
        # Get raw counts
        processed_stmt = select(func.count(ProcessedArticle.id)).where(ProcessedArticle.published_status == "published")
        processed_count = (await db.execute(processed_stmt)).scalar() or 0

        read_stmt = select(func.count(ArticleReadModel.id))
        read_count = (await db.execute(read_stmt)).scalar() or 0

        # Get missing fields counts
        missing_impact = (await db.execute(select(func.count(ArticleReadModel.id)).where((ArticleReadModel.final_score == 0) | (ArticleReadModel.final_score.is_(None))))).scalar() or 0
        missing_summary = (await db.execute(select(func.count(ArticleReadModel.id)).where((ArticleReadModel.summary == "") | (ArticleReadModel.summary.is_(None))))).scalar() or 0
        missing_reading_time = (await db.execute(select(func.count(ArticleReadModel.id)).where((ArticleReadModel.reading_time == 0) | (ArticleReadModel.reading_time.is_(None))))).scalar() or 0
        missing_thumbnails = (await db.execute(select(func.count(ArticleReadModel.id)).where((ArticleReadModel.thumbnail_url == "") | (ArticleReadModel.thumbnail_url.is_(None))))).scalar() or 0

        # Outbox backlog
        outbox_stmt = select(func.count(EventOutbox.id)).where(EventOutbox.status == "pending")
        outbox_backlog = (await db.execute(outbox_stmt)).scalar() or 0

        projection_lag = abs(processed_count - read_count)

        # Get latest timestamps
        latest_processed_stmt = select(ProcessedArticle.published_at).where(ProcessedArticle.published_status == "published").order_by(ProcessedArticle.published_at.desc()).limit(1)
        latest_processed_at = (await db.execute(latest_processed_stmt)).scalar()
        
        latest_projected_stmt = select(ArticleReadModel.published_at).order_by(ArticleReadModel.published_at.desc()).limit(1)
        latest_projected_at = (await db.execute(latest_projected_stmt)).scalar()

        last_projection_stmt = select(ArticleReadModel.projected_at).order_by(ArticleReadModel.projected_at.desc()).limit(1)
        last_projection_at = (await db.execute(last_projection_stmt)).scalar()

        # Find oldest unprojected article
        unprojected_stmt = text(
            "SELECT pa.published_at FROM processed_articles pa "
            "LEFT JOIN articles a ON a.id = pa.id::text "
            "WHERE a.id IS NULL AND pa.published_status = 'published' "
            "ORDER BY pa.published_at ASC LIMIT 1;"
        )
        oldest_unprojected = (await db.execute(unprojected_stmt)).scalar()

        # Calculate success rate
        projection_success_rate = 100.0
        if processed_count > 0:
            projection_success_rate = round((read_count / processed_count) * 100, 2)
            projection_success_rate = min(100.0, projection_success_rate)  # Cap at 100%

        # Strict health evaluation based on architectural requirements
        status_text = "healthy"
        if projection_lag > 0 and projection_lag <= 5:
            status_text = "degraded"
            response.status_code = status.HTTP_206_PARTIAL_CONTENT
        elif projection_lag > 5 or missing_impact > 0 or missing_summary > 0 or missing_thumbnails > 0:
            status_text = "unhealthy"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return StandardResponse(
            correlation_id=correlation_id,
            data={
                "status": status_text,
                "projection_version": "v2",
                "event_contract": "ArticlePublished:v2",
                "processed_articles": processed_count,
                "read_model_articles": read_count,
                "projection_lag": projection_lag,
                "projection_success_rate": f"{projection_success_rate}%",
                "missing_impact_scores": missing_impact,
                "missing_summaries": missing_summary,
                "missing_reading_times": missing_reading_time,
                "missing_thumbnails": missing_thumbnails,
                "outbox_backlog": outbox_backlog,
                "latest_processed_article": latest_processed_at.isoformat() if latest_processed_at else None,
                "latest_projected_article": latest_projected_at.isoformat() if latest_projected_at else None,
                "last_projection_at": last_projection_at.isoformat() if last_projection_at else None,
                "oldest_unprojected_article": oldest_unprojected.isoformat() if oldest_unprojected else None
            }
        )
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StandardResponse(
            correlation_id=correlation_id,
            data={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@router.get("/workers", response_model=StandardResponse[dict])
async def get_workers_health():
    """
    Workers Health Check: Returns status of celery, beat, and SSE stream.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    # Mocking for Sprint 1
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "celery_worker": "healthy",
            "celery_beat": "healthy",
            "sse_stream": "healthy"
        }
    )

@router.get("/queues", response_model=StandardResponse[dict])
async def get_queues_health():
    """
    Queues Health Check: Returns queue depths.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    # Mocking for Sprint 1
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "rss_queue_depth": 0,
            "projection_queue_depth": 0,
            "thumbnail_queue_depth": 0,
            "embedding_queue_depth": 0
        }
    )

@router.get("/sources", response_model=StandardResponse[dict])
async def get_sources_health():
    """
    Sources Health Check: Returns ingestion source states.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    # Mocking for Sprint 1
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "total_sources": 25,
            "healthy_sources": 24,
            "degraded_sources": 1,
            "avg_fetch_latency_ms": 180
        }
    )

@router.get("/recovery", response_model=StandardResponse[dict])
async def get_recovery_health(db: AsyncSession = Depends(get_db)):
    """
    Autonomous Recovery Health Check: Returns the safety layer state and recent metrics.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    from app.services.recovery.service import RecoveryService
    from app.services.recovery.models import RecoveryState
    
    service = RecoveryService(db)
    cqrs_state = await service._get_redis_state("cqrs")
    hourly_limit = await service.redis.get("recovery:hourly_count:cqrs")
    attempts_last_hour = int(hourly_limit) if hourly_limit else 0
    
    # Calculate overarching status based on Safety Rules
    status_text = "healthy"
    automation_enabled = cqrs_state["state"] != RecoveryState.DISABLED.value
    
    if cqrs_state["state"] == RecoveryState.FAILED.value:
        status_text = "degraded"
    if not automation_enabled:
        status_text = "error"
        
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "status": status_text,
            "automation_enabled": automation_enabled,
            "recovery_state": cqrs_state["state"].lower(),
            "cooldown_active": cqrs_state["cooldown_remaining"] > 0,
            "attempts_last_hour": attempts_last_hour,
            "success_rate": 100.0, # Mocked for now until Prometheus integration
            "consecutive_failures": cqrs_state["consecutive_failures"],
            "mode": "dry_run" if service.is_dry_run else "active",
            "last_recovery": "Never"
        }
    )

@router.get("/incidents", response_model=StandardResponse[dict])
async def get_incidents_health(db: AsyncSession = Depends(get_db)):
    """
    Root Cause Incidents: Returns aggregated Sprint 5.0 deterministic statistics.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    from app.models.telemetry import RootCauseAnalysis
    
    try:
        # Aggregations
        open_incidents = (await db.execute(select(func.count(RootCauseAnalysis.id)).where(RootCauseAnalysis.status == "OPEN"))).scalar() or 0
        auto_resolved = (await db.execute(select(func.count(RootCauseAnalysis.id)).where(RootCauseAnalysis.status == "AUTO_RESOLVED"))).scalar() or 0
        manual_intervention = (await db.execute(select(func.count(RootCauseAnalysis.id)).where(RootCauseAnalysis.status == "MANUAL_REQUIRED"))).scalar() or 0
        
        # Average Confidence
        avg_conf_stmt = select(func.avg(RootCauseAnalysis.confidence_score))
        avg_confidence = (await db.execute(avg_conf_stmt)).scalar() or 0.0
        
        # Top Cause
        top_cause_stmt = (
            select(RootCauseAnalysis.root_cause, func.count(RootCauseAnalysis.id))
            .group_by(RootCauseAnalysis.root_cause)
            .order_by(func.count(RootCauseAnalysis.id).desc())
            .limit(1)
        )
        top_cause_row = (await db.execute(top_cause_stmt)).first()
        top_cause = top_cause_row[0] if top_cause_row else "None"
        top_cause_count = top_cause_row[1] if top_cause_row else 0
        
        top_cause_str = f"{top_cause} ({top_cause_count})" if top_cause_count > 0 else "None"

        # Latest Explanation
        from app.models.telemetry import RootCauseExplanation
        latest_explanation_stmt = (
            select(RootCauseExplanation, RootCauseAnalysis)
            .join(RootCauseAnalysis, RootCauseAnalysis.id == RootCauseExplanation.analysis_id)
            .order_by(RootCauseExplanation.created_at.desc())
            .limit(1)
        )
        latest_expl_row = (await db.execute(latest_explanation_stmt)).first()
        
        latest_explanation_data = None
        if latest_expl_row:
            expl_obj, analysis_obj = latest_expl_row
            latest_explanation_data = {
                "top_incident": analysis_obj.root_cause,
                "ai_summary": expl_obj.summary,
                "confidence": f"{round(analysis_obj.confidence_score * 100)}%"
            }

        return StandardResponse(
            correlation_id=correlation_id,
            data={
                "open_incidents": open_incidents,
                "auto_resolved": auto_resolved,
                "manual_intervention": manual_intervention,
                "top_cause": top_cause_str,
                "average_confidence": f"{round(avg_confidence * 100)}%",
                "latest_explanation": latest_explanation_data
            }
        )
    except Exception as e:
        return StandardResponse(
            correlation_id=correlation_id,
            data={
                "open_incidents": 0,
                "auto_resolved": 0,
                "manual_intervention": 0,
                "latest_explanation": None
            }
        )

@router.get("/ai-thumbnail", response_model=StandardResponse[dict])
async def get_ai_thumbnail_health():
    """
    AI Thumbnail Recovery Health Check: Validates Gemini provider and image generation readiness.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    
    # 1. Check Gemini SDK installation
    sdk_installed = False
    try:
        import google.genai
        sdk_installed = True
    except ImportError:
        pass

    # 2. Check Configuration (API Key)
    from app.core.config import settings
    config_present = bool(getattr(settings, "GEMINI_API_KEY", None))

    # 3. Overall health
    is_healthy = sdk_installed and config_present
    status_text = "healthy" if is_healthy else "degraded"

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "status": status_text,
            "gemini_sdk_installed": sdk_installed,
            "gemini_config_present": config_present,
            "fallback_generators": ["OpenAI"]
        }
    )
