import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import log_audit
from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.core.security import require_role
from app.models.article import ProcessedArticle
from app.models.growth import FeatureFlag
from app.models.source import Source
from app.models.user import AIJobHistory, ArticleRevision, AuditLog, Role, User
from app.schemas.admin import (
    AI_CostAggregationResponse,
    AIJobHistoryResponse,
    NotificationListResponse,
)
from app.schemas.responses import PaginatedResponse, PaginationMetadata, StandardResponse

logger = logging.getLogger("tech_news.admin")
router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic Schemas for Request Payloads
# ---------------------------------------------------------------------------


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="Target role name (e.g. reader, editor, admin, super_admin)")


class UserStatusUpdate(BaseModel):
    status: str = Field(..., description="Target status name (active, disabled, suspended)")


class FeatureFlagToggle(BaseModel):
    enabled: bool


class EmergencySwitchRequest(BaseModel):
    state: bool = Field(..., description="True to enable emergency pipeline cutoff, False to resume operations")


class ArticleModerationRequest(BaseModel):
    action: str = Field(..., description="Action to perform: approve, reject, draft, publish")


class SourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1)
    url: str | None = Field(None, min_length=1)
    crawl_interval: int | None = Field(None, ge=60)
    credibility_score: int | None = Field(None, ge=0, le=100)
    category: str | None = Field(None, min_length=1)


class ArticleUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)
    summary: str | None = Field(None, min_length=1)
    tags: str | None = Field(None)


# ---------------------------------------------------------------------------
# 1. Dashboard Telemetry & System Status
# ---------------------------------------------------------------------------

from app.core.redis import get_redis_client
from app.schemas.monitoring import InfrastructureResponse, OverviewResponse, VersionedTelemetryEnvelope
from app.services.monitoring.observability import (
    run_infrastructure_health_checks,
    run_overview_health_checks,
    run_queue_health_checks,
)
from app.services.monitoring.repository import MonitoringRepository


@router.get("/overview", response_model=StandardResponse[VersionedTelemetryEnvelope[OverviewResponse]])
async def get_overview(
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Returns cached high-level platform summary counts (sources, articles, AI queue).
    """
    correlation_id = correlation_id_ctx.get() or "system"
    repo = MonitoringRepository()

    overview = await repo.get_overview()
    if not overview:
        await run_overview_health_checks()
        overview = await repo.get_overview()

    envelope = VersionedTelemetryEnvelope(
        schema_version=1,
        generated_at=overview.get("generated_at", datetime.now(timezone.utc).isoformat())
        if overview
        else datetime.now(timezone.utc).isoformat(),
        data=overview or {},
    )
    return StandardResponse(correlation_id=correlation_id, data=envelope)


@router.get("/infrastructure", response_model=StandardResponse[VersionedTelemetryEnvelope[InfrastructureResponse]])
async def get_infrastructure_health(
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Returns the current health status of the 6 backend infrastructure services
    plus calculated overall score & grade and lightweight rolling history.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    repo = MonitoringRepository()

    services = ["postgres", "redis", "worker", "beat", "backend"]
    services_data = {}

    # Check if we have snapshots. If not, trigger a check inline
    any_missing = False
    for s in services:
        snapshot = await repo.get_health_snapshot(s)
        if not snapshot:
            any_missing = True
            break

    if any_missing:
        await run_infrastructure_health_checks()

    # Compile snapshots and histories
    for s in services:
        snapshot = await repo.get_health_snapshot(s)
        history = await repo.get_history(s)
        services_data[s] = {"snapshot": snapshot, "history": history}

    # Get overall health score cached key
    client = get_redis_client()
    score_data = await client.get("telemetry:v2:health_score")
    if score_data:
        try:
            import json

            score_payload = json.loads(score_data)
        except Exception:
            score_payload = {"score": 100, "grade": "A+"}
    else:
        score_payload = {"score": 100, "grade": "A+"}

    infra_payload = {"health_score": score_payload, "services": services_data}

    envelope = VersionedTelemetryEnvelope(
        schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(), data=infra_payload
    )
    return StandardResponse(correlation_id=correlation_id, data=envelope)


@router.get("/queue", response_model=StandardResponse[VersionedTelemetryEnvelope])
async def get_queue_telemetry(
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Returns current queue depth, jobs/min, and growth rate telemetry.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    repo = MonitoringRepository()

    queue = await repo.get_queue()
    if not queue:
        await run_queue_health_checks()
        queue = await repo.get_queue()

    envelope = VersionedTelemetryEnvelope(
        schema_version=1,
        generated_at=queue.get("last_checked", datetime.now(timezone.utc).isoformat())
        if queue
        else datetime.now(timezone.utc).isoformat(),
        data=queue or {},
    )
    return StandardResponse(correlation_id=correlation_id, data=envelope)


@router.get("/metrics", response_model=StandardResponse[VersionedTelemetryEnvelope])
async def get_extensible_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Returns extensible aggregated metrics for Postgres, Redis, Queue, and Thumbnail pipeline.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    repo = MonitoringRepository()

    # 1. Database and Redis
    postgres_snap = await repo.get_health_snapshot("postgres")
    redis_snap = await repo.get_health_snapshot("redis")
    queue_snap = await repo.get_queue()

    postgres_metrics = postgres_snap.metrics if postgres_snap else {}
    redis_metrics = redis_snap.metrics if redis_snap else {}
    queue_metrics = queue_snap.get("metrics", {}) if queue_snap else {}

    # 2. Thumbnail pipeline quality metrics
    thumbnail_metrics = {}
    try:
        total_stmt = select(func.count(ProcessedArticle.id))
        total_res = await db.execute(total_stmt)
        total_count = total_res.scalar() or 0

        valid_stmt = select(func.count(ProcessedArticle.id)).where(ProcessedArticle.thumbnail_url.isnot(None))
        valid_res = await db.execute(valid_stmt)
        valid_count = valid_res.scalar() or 0

        missing_stmt = select(func.count(ProcessedArticle.id)).where(ProcessedArticle.thumbnail_url.is_(None))
        missing_res = await db.execute(missing_stmt)
        missing_count = missing_res.scalar() or 0

        avg_res_stmt = select(func.avg(ProcessedArticle.thumbnail_width * ProcessedArticle.thumbnail_height)).where(
            ProcessedArticle.thumbnail_width.isnot(None)
        )
        avg_res = (await db.execute(avg_res_stmt)).scalar() or 0

        # Source Distribution
        sources_stmt = (
            select(ProcessedArticle.thumbnail_source, func.count(ProcessedArticle.id))
            .where(ProcessedArticle.thumbnail_source.isnot(None))
            .group_by(ProcessedArticle.thumbnail_source)
        )
        sources_res = await db.execute(sources_stmt)
        sources_dist = {row[0]: row[1] for row in sources_res.all()}

        coverage_rate = round((valid_count / total_count) * 100.0, 2) if total_count > 0 else 0.0
        missing_rate = round((missing_count / total_count) * 100.0, 2) if total_count > 0 else 0.0

        thumbnail_metrics = {
            "total_processed": total_count,
            "coverage_rate": coverage_rate,
            "missing_rate": missing_rate,
            "average_resolution_pixels": int(avg_res),
            "source_distribution": sources_dist,
        }
    except Exception as e:
        logger.warning(f"Metrics: failed to retrieve thumbnail metrics: {e}")

    metrics_payload = {
        "postgres": postgres_metrics,
        "redis": redis_metrics,
        "queue": queue_metrics,
        "thumbnails": thumbnail_metrics,
    }

    envelope = VersionedTelemetryEnvelope(
        schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(), data=metrics_payload
    )
    return StandardResponse(correlation_id=correlation_id, data=envelope)


@router.get("/logs", response_model=StandardResponse[list])
async def get_recent_logs(
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Returns the cached rolling pipeline log events.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    import typing
    client = typing.cast(typing.Any, get_redis_client())

    items = await client.lrange("recent_events", 0, -1)
    events = []
    for item in items:
        try:
            val = item.decode("utf-8") if isinstance(item, bytes) else item
            import json

            events.append(json.loads(val))
        except Exception:
            pass

    return StandardResponse(correlation_id=correlation_id, data=events)


@router.get("/notifications", response_model=StandardResponse[NotificationListResponse])
async def get_admin_notifications(
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Returns unread administrative notifications.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    return StandardResponse(correlation_id=correlation_id, data={"notifications": [], "unread": 0})


# ---------------------------------------------------------------------------
# 2. Newsroom Sources Management
# ---------------------------------------------------------------------------


@router.get("/sources", response_model=StandardResponse[list])
async def list_admin_sources(
    show_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    List all registered crawler sources in the dashboard registry with enabled/disabled states.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(Source)
    if not show_deleted:
        stmt = stmt.where(Source.is_deleted == False)
    stmt = stmt.order_by(Source.id.asc())
    result = await db.execute(stmt)
    sources = result.scalars().all()

    return StandardResponse(
        correlation_id=correlation_id,
        data=[
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "method": s.method,
                "url": s.url,
                "credibility_score": s.credibility_score,
                "crawl_interval": s.crawl_interval,
                "enabled": s.enabled,
                "health_state": s.health_state,
                "total_crawls": s.total_crawls,
                "successful_crawls": s.successful_crawls,
                "reliability_score": s.reliability_score,
                "last_crawl_at": s.last_crawl_at.isoformat() if s.last_crawl_at else None,
                "is_deleted": s.is_deleted,
                "created_at": s.created_at.isoformat(),
            }
            for s in sources
        ],
    )


@router.post("/diagnostic/run-migrations")
async def run_migrations(current_user: User = Depends(require_role("super_admin"))):
    import subprocess
    import os
    import asyncio

    def _do_run():
        ini_path = os.path.join(os.getcwd(), "alembic.ini")
        return subprocess.run(
            ["alembic", "-c", ini_path, "upgrade", "head"],
            capture_output=True,
            text=True,
        )

    try:
        res = await asyncio.to_thread(_do_run)
        if res.returncode == 0:
            return {"status": "success", "stdout": res.stdout, "stderr": res.stderr}
        else:
            return {"status": "error", "returncode": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/diagnostic/db-truth")
async def get_db_truth(db: AsyncSession = Depends(get_db)):
    """
    Forensic diagnostic endpoint to get exact counts and status distribution.
    """
    from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel
    from sqlalchemy import func, select
    
    # 1. RawArticle counts
    raw_total = await db.scalar(select(func.count(RawArticle.id)))
    
    raw_status_res = await db.execute(select(RawArticle.status, func.count(RawArticle.id)).group_by(RawArticle.status))
    raw_status_dist = {str(k): v for k, v in raw_status_res.all()}
    
    dead_letter_res = await db.execute(
        select(RawArticle.dead_letter_reason, func.count(RawArticle.id))
        .where(RawArticle.dead_letter_reason.isnot(None))
        .group_by(RawArticle.dead_letter_reason)
    )
    dead_letter_dist = {str(k): v for k, v in dead_letter_res.all()}
    
    try:
        filter_reason_res = await db.execute(
            select(getattr(RawArticle, "filter_reason", RawArticle.error_log), func.count(RawArticle.id))
            .where(RawArticle.status == "filtered")
            .group_by(getattr(RawArticle, "filter_reason", RawArticle.error_log))
        )
        filter_reasons = {str(k): v for k, v in filter_reason_res.all()}
    except Exception as e:
        filter_reasons = {"error": str(e)}

    # 2. ProcessedArticle counts
    processed_total = await db.scalar(select(func.count(ProcessedArticle.id)))
    
    # 3. ArticleReadModel counts
    read_total = await db.scalar(select(func.count(ArticleReadModel.id)))
    
    return {
        "raw_total": raw_total,
        "raw_status_dist": raw_status_dist,
        "dead_letter_dist": dead_letter_dist,
        "filter_reasons": filter_reasons,
        "processed_total": processed_total,
        "read_total": read_total
    }

@router.get("/diagnostic/filtered-samples")
async def get_filtered_samples(limit: int = 5, db: AsyncSession = Depends(get_db)):
    """
    Forensic endpoint to dump sample filtered RawArticles for Phase 0 extraction debugging.
    """
    from app.models.article import RawArticle
    from sqlalchemy import select
    
    res = await db.execute(
        select(RawArticle)
        .where(RawArticle.status == "filtered")
        .limit(limit)
    )
    articles = res.scalars().all()
    
    return {
        "samples": [
            {
                "id": a.id,
                "url": a.url,
                "source_id": a.source_id,
                "error_log": a.error_log,
                "dead_letter_reason": a.dead_letter_reason,
                "article_metadata": a.article_metadata,
            }
            for a in articles
        ]
    }


# ---------------------------------------------------------------------------
# 3. Editorial & Article Moderation
# ---------------------------------------------------------------------------


@router.get("/root-cause/timeline/{timeline_correlation_id}", response_model=StandardResponse[dict])
async def get_root_cause_timeline(
    timeline_correlation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Fetches the causal timeline chain of events for a given correlation ID.
    This serves as the deterministic foundation for Sprint 5 AI reasoning.
    """
    system_correlation_id = correlation_id_ctx.get() or "system"
    
    stmt = select(TimelineNode).where(TimelineNode.correlation_id == timeline_correlation_id).order_by(TimelineNode.id.asc())
    res = await db.execute(stmt)
    nodes = res.scalars().all()
    
    if not nodes:
        return StandardResponse(
            correlation_id=system_correlation_id,
            data={
                "correlation_id": timeline_correlation_id,
                "timeline": []
            }
        )
        
    return StandardResponse(
        correlation_id=system_correlation_id,
        data={
            "correlation_id": timeline_correlation_id,
            "timeline": [
                {
                    "id": node.id,
                    "node_type": node.node_type.value if hasattr(node.node_type, 'value') else node.node_type,
                    "title": node.title,
                    "description": node.description,
                    "timestamp": node.timestamp.isoformat(),
                    "caused_by_id": node.caused_by_id,
                    "metadata": node.metadata_json
                }
                for node in nodes
            ]
        }
    )

@router.get("/ai/jobs", response_model=StandardResponse[list[AIJobHistoryResponse]])
async def list_ai_job_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Retrieve historical logs of AI processing jobs.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(AIJobHistory).order_by(AIJobHistory.id.desc()).limit(limit)
    res = await db.execute(stmt)
    jobs = res.scalars().all()

    return StandardResponse(
        correlation_id=correlation_id,
        data=[
            {
                "id": j.id,
                "raw_article_id": j.raw_article_id,
                "processed_article_id": j.processed_article_id,
                "status": j.status,
                "provider": j.provider,
                "model_name": j.model,
                "task_type": j.task_type,
                "prompt_version": j.prompt_version,
                "tokens_prompt": j.prompt_tokens,
                "tokens_completion": j.completion_tokens,
                "total_tokens": j.total_tokens,
                "cost_usd": float(j.cost_usd),
                "latency_ms": j.latency_ms,
                "cache_hit": j.cache_hit,
                "retry_count": j.retry_count,
                "error_message": j.error_message or j.error,
                "created_at": j.created_at.isoformat(),
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.finished_at.isoformat() if j.finished_at else None,
            }
            for j in jobs
        ],
    )


@router.get("/ai/costs", response_model=StandardResponse[AI_CostAggregationResponse])
async def aggregate_ai_costs(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Aggregate total AI API tokens consumption and financial expenses.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    stmt = select(
        func.sum(AIJobHistory.prompt_tokens), func.sum(AIJobHistory.completion_tokens), func.sum(AIJobHistory.cost_usd)
    )
    res = await db.execute(stmt)
    prompt_tokens, completion_tokens, total_cost = res.first() or (0, 0, 0.0)

    # Cost breakdown by model
    breakdown_stmt = select(AIJobHistory.model, func.sum(AIJobHistory.cost_usd), func.count(AIJobHistory.id)).group_by(
        AIJobHistory.model
    )
    breakdown_res = await db.execute(breakdown_stmt)

    breakdown_list = [
        {"model": model, "cost": float(cost), "jobs_count": count}
        for model, cost, count in breakdown_res.all()
        if model
    ]

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "aggregated": {
                "prompt_tokens": prompt_tokens or 0,
                "completion_tokens": completion_tokens or 0,
                "total_tokens": (prompt_tokens or 0) + (completion_tokens or 0),
                "total_cost_usd": float(total_cost or 0.0),
            },
            "models_breakdown": breakdown_list,
        },
    )


# ---------------------------------------------------------------------------
# 7. System Emergency & Feature Flags
# ---------------------------------------------------------------------------


@router.get("/emergency-switch", response_model=StandardResponse[dict])
async def get_emergency_switch_state(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """
    Check the current status of the emergency ingestion pipeline cutoff switch.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(FeatureFlag).where(FeatureFlag.key == "emergency_pipeline_cutoff")
    res = await db.execute(stmt)
    flag = res.scalars().first()
    cutoff_active = flag.default_value if flag else False

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "cutoff_active": cutoff_active,
            "message": "Emergency ingestion pipeline cutoff is currently "
            + ("ACTIVE" if cutoff_active else "INACTIVE")
            + ".",
        },
    )


@router.post("/emergency-switch/toggle", response_model=StandardResponse[dict])
async def toggle_emergency_switch(
    request: Request,
    payload: EmergencySwitchRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """
    Trigger emergency cutoff to halt all crawler engines and scraping queues immediately.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    stmt = select(FeatureFlag).where(FeatureFlag.key == "emergency_pipeline_cutoff")
    res = await db.execute(stmt)
    flag = res.scalars().first()

    if not flag:
        flag = FeatureFlag(
            key="emergency_pipeline_cutoff",
            default_value=payload.state,
            environment_states={"production": payload.state},
            description="Globally cutoff all ingestion, crawling, and AI parsing engines during operational incidents.",
        )
        db.add(flag)
    else:
        flag.default_value = payload.state
        states = dict(flag.environment_states) if flag.environment_states else {}
        states["production"] = payload.state
        flag.environment_states = states
        flag.updated_at = datetime.now(timezone.utc)

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="TOGGLE_EMERGENCY_CUTOFF",
        resource="system:pipeline",
        metadata={"cutoff_active": flag.default_value},
        ip_address=ip,
    )
    await db.commit()

    logger.warning(
        f"CRITICAL: Emergency pipeline cutoff has been set to {flag.default_value} by super admin user {current_user.email}!"
    )
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "cutoff_active": flag.default_value,
            "message": "Successfully updated emergency cutoff active state to "
            + ("ACTIVE" if flag.default_value else "INACTIVE")
            + ".",
        },
    )

class ReplayRequest(BaseModel):
    article_ids: list[int] | None = Field(None, description="List of RawArticle IDs to replay")
    filter_reason: str | None = Field(None, description="Filter reason to replay (e.g. RELEVANCE_FAILED_KEYWORD_DENSITY)")

@router.post("/diagnostic/replay", response_model=StandardResponse)
async def trigger_article_replay(
    request: ReplayRequest,
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Trigger background Celery task to replay filtered articles.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    from app.tasks.admin import replay_filtered_articles
    
    # Enqueue celery task
    replay_filtered_articles.delay(
        article_ids=request.article_ids,
        filter_reason=request.filter_reason
    )
    
    logger.info(f"Admin {current_user.email} triggered article replay for ids={request.article_ids} reason={request.filter_reason}")
    
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "message": "Replay task enqueued successfully.",
            "enqueued_ids": request.article_ids,
            "enqueued_reason": request.filter_reason
        }
    )
