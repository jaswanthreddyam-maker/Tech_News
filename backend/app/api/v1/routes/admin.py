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


@router.patch("/sources/{id}", response_model=StandardResponse[dict])
async def update_admin_source(
    request: Request,
    id: int,
    payload: SourceUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Update configuration settings for a crawler source.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(Source).where(Source.id == id)
    res = await db.execute(stmt)
    source = res.scalars().first()

    if not source or source.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source ID {id} not found.")

    updated_fields = {}
    if payload.name is not None:
        source.name = payload.name
        updated_fields["name"] = payload.name
    if payload.url is not None:
        source.url = payload.url
        updated_fields["url"] = payload.url
    if payload.crawl_interval is not None:
        source.crawl_interval = payload.crawl_interval
        updated_fields["crawl_interval"] = payload.crawl_interval
    if payload.credibility_score is not None:
        source.credibility_score = payload.credibility_score
        updated_fields["credibility_score"] = payload.credibility_score
    if payload.category is not None:
        source.category = payload.category
        updated_fields["category"] = payload.category

    if not updated_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update.")

    await db.commit()

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="UPDATE_SOURCE",
        resource=f"source:{source.id}",
        metadata={"updated": updated_fields},
        ip_address=ip,
    )
    await db.commit()

    logger.info(f"Admin: Updated source '{source.name}' settings: {updated_fields}.")
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "source_id": source.id,
            "message": f"Successfully updated source '{source.name}' configuration settings.",
        },
    )


@router.delete("/sources/{id}", response_model=StandardResponse[dict])
async def delete_admin_source(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Soft-delete a specific crawler source.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(Source).where(Source.id == id)
    res = await db.execute(stmt)
    source = res.scalars().first()

    if not source or source.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source ID {id} not found.")

    source.is_deleted = True
    await db.commit()

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="DELETE_SOURCE",
        resource=f"source:{id}",
        metadata={"name": source.name},
        ip_address=ip,
    )
    await db.commit()

    logger.info(f"Admin: Soft-deleted source '{source.name}' (ID: {id}).")
    return StandardResponse(
        correlation_id=correlation_id,
        data={"source_id": id, "message": f"Successfully soft-deleted source '{source.name}'."},
    )


@router.post("/sources/{id}/restore", response_model=StandardResponse[dict])
async def restore_admin_source(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Restore a soft-deleted crawler source.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(Source).where(Source.id == id)
    res = await db.execute(stmt)
    source = res.scalars().first()

    if not source or not source.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source ID {id} not found or not deleted.")

    source.is_deleted = False
    await db.commit()

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="RESTORE_SOURCE",
        resource=f"source:{id}",
        metadata={"name": source.name},
        ip_address=ip,
    )
    await db.commit()

    logger.info(f"Admin: Restored soft-deleted source '{source.name}' (ID: {id}).")
    return StandardResponse(
        correlation_id=correlation_id,
        data={"source_id": id, "message": f"Successfully restored source '{source.name}'."},
    )


@router.post("/sources/{id}/toggle", response_model=StandardResponse[dict])
async def toggle_admin_source(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Enable or disable a specific technology news source globally.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(Source).where(Source.id == id)
    res = await db.execute(stmt)
    source = res.scalars().first()

    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source ID {id} not found.")

    source.enabled = not source.enabled
    await db.commit()

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="TOGGLE_SOURCE",
        resource=f"source:{source.id}",
        metadata={"name": source.name, "enabled": source.enabled},
        ip_address=ip,
    )
    await db.commit()

    logger.info(f"Admin: Toggled source '{source.name}' active state to {source.enabled}.")
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "source_id": source.id,
            "name": source.name,
            "enabled": source.enabled,
            "message": f"Successfully toggled active state for source '{source.name}' to {source.enabled}.",
        },
    )


@router.post("/sources/{id}/trigger", response_model=StandardResponse[dict])
async def trigger_admin_source_crawl(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Dispatch an asynchronous force crawl for a specific source via Celery.
    Returns immediately with a task ID — crawl executes in the background worker.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    logger.info(f"Admin: Force crawl requested for source ID {id} by user {current_user.email}...")

    # Validate source exists and is enabled before dispatching
    stmt = select(Source).where(Source.id == id)
    res = await db.execute(stmt)
    source = res.scalars().first()

    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source ID {id} not found.")
    if not source.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Source '{source.name}' is currently disabled."
        )

    # Dispatch to Celery worker asynchronously
    from celery_app import force_crawl_source_task

    task = force_crawl_source_task.delay(id)

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="TRIGGER_CRAWL",
        resource=f"source:{id}",
        metadata={"task_id": task.id, "source_name": source.name},
        ip_address=ip,
    )
    await db.commit()

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "source_id": id,
            "status": "accepted",
            "task_id": task.id,
            "message": f"Force crawl dispatched for source '{source.name}'. Processing in background.",
        },
    )


# ---------------------------------------------------------------------------
# 3. Editorial & Article Moderation
# ---------------------------------------------------------------------------


@router.get("/articles/pending", response_model=StandardResponse[list])
async def list_pending_articles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    List all processed articles currently in 'draft' or 'review' states awaiting editor validation.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = (
        select(ProcessedArticle)
        .where(ProcessedArticle.published_status.in_(["draft", "review"]))
        .order_by(ProcessedArticle.created_at.desc())
    )
    result = await db.execute(stmt)
    articles = result.scalars().all()

    return StandardResponse(
        correlation_id=correlation_id,
        data=[
            {
                "id": a.id,
                "title": a.title,
                "slug": a.slug,
                "summary": a.summary,
                "why_this_matters": getattr(a, "why_this_matters", None),
                "content": a.content,
                "tags": a.tags,
                "source_name": a.source_name,
                "ai_confidence": a.ai_confidence,
                "published_status": a.published_status,
                "created_at": a.created_at.isoformat(),
            }
            for a in articles
        ],
    )


@router.post("/articles/{id}/moderate", response_model=StandardResponse[dict])
async def moderate_processed_article(
    request: Request,
    id: int,
    payload: ArticleModerationRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Moderation endpoint for approving, rejecting or publishing articles.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    action = payload.action.lower()

    stmt = select(ProcessedArticle).where(ProcessedArticle.id == id)
    res = await db.execute(stmt)
    article = res.scalars().first()

    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Article ID {id} not found.")

    old_status = article.published_status

    if action == "publish":
        article.published_status = "published"
        article.published_at = datetime.now(timezone.utc)
    elif action == "reject":
        article.published_status = "rejected"
    elif action == "draft":
        article.published_status = "draft"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported moderation action '{action}'")

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="MODERATE_ARTICLE",
        resource=f"article:{article.id}",
        metadata={"old_status": old_status, "new_status": article.published_status, "action": action},
        ip_address=ip,
    )
    await db.commit()

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "article_id": article.id,
            "action_taken": action,
            "status": "success",
            "message": f"Successfully transitioned article {id} state from '{old_status}' to '{article.published_status}'.",
        },
    )


@router.patch("/articles/{id}", response_model=StandardResponse[dict])
async def update_pending_article(
    request: Request,
    id: int,
    payload: ArticleUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Update Title, Summary, and Tags of a processed article, tracking revisions automatically.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(ProcessedArticle).where(ProcessedArticle.id == id)
    res = await db.execute(stmt)
    article = res.scalars().first()

    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Article ID {id} not found.")

    # 1. Fetch max existing revision_number for the article
    rev_stmt = select(func.max(ArticleRevision.revision_number)).where(ArticleRevision.article_id == id)
    rev_res = await db.execute(rev_stmt)
    max_rev = rev_res.scalar() or 0
    next_rev = max_rev + 1

    # 2. Create and add an ArticleRevision record copy of the CURRENT article state before updates are applied
    revision = ArticleRevision(
        article_id=article.id,
        user_id=current_user.id,
        title=article.title,
        summary=article.summary,
        tags=article.tags,
        content=article.content,
        revision_number=next_rev,
    )
    db.add(revision)

    # 3. Apply the edits
    updated_fields = {}
    if payload.title is not None:
        article.title = payload.title
        # dynamically recalculate the slug if title is updated
        import re

        slug = payload.title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "-", slug).strip("-")

        base_slug = slug
        suffix = 1
        while True:
            dup_stmt = select(ProcessedArticle).where(ProcessedArticle.slug == slug, ProcessedArticle.id != id)
            dup_res = await db.execute(dup_stmt)
            if not dup_res.scalars().first():
                break
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        article.slug = slug
        updated_fields["title"] = payload.title
        updated_fields["slug"] = slug

    if payload.summary is not None:
        article.summary = payload.summary
        updated_fields["summary"] = payload.summary

    if payload.tags is not None:
        article.tags = payload.tags
        updated_fields["tags"] = payload.tags

    await db.commit()

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="UPDATE_ARTICLE",
        resource=f"article:{article.id}",
        metadata={"updated": updated_fields, "revision_number": next_rev},
        ip_address=ip,
    )
    await db.commit()

    logger.info(f"Admin: Article ID {article.id} updated by {current_user.email}. Revision {next_rev} created.")
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "article_id": article.id,
            "revision_number": next_rev,
            "message": f"Successfully updated article and saved revision snapshot #{next_rev}.",
        },
    )


@router.get("/articles/{id}/revisions", response_model=StandardResponse[list])
async def list_article_revisions(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    List all revisions of a specific article.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = (
        select(ArticleRevision)
        .options(selectinload(ArticleRevision.user))
        .where(ArticleRevision.article_id == id)
        .order_by(ArticleRevision.revision_number.desc())
    )
    res = await db.execute(stmt)
    revisions = res.scalars().all()
    return StandardResponse(
        correlation_id=correlation_id,
        data=[
            {
                "id": r.id,
                "revision_number": r.revision_number,
                "user_id": r.user_id,
                "user_email": r.user.email if r.user else "Unknown User",
                "title": r.title,
                "summary": r.summary,
                "why_this_matters": getattr(r, "why_this_matters", None),
                "tags": r.tags,
                "created_at": r.created_at.isoformat(),
            }
            for r in revisions
        ],
    )

# ---------------------------------------------------------------------------
# 4. Replay Explorer (Recovery System)
# ---------------------------------------------------------------------------
from app.services.replay_service import ReplayService

@router.post("/replay/projection/{article_id}", response_model=StandardResponse[dict])
async def admin_replay_projection(
    request: Request,
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Idempotent recovery: Synthesizes a replay of the ArticleProjector for a specific ProcessedArticle.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    service = ReplayService(db)
    
    await service.replay_projection(str(article_id), current_user.email)
    
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "article_id": article_id,
            "status": "success",
            "message": f"Successfully replayed projection for article {article_id}.",
        },
    )

@router.post("/replay/event/{event_id}", response_model=StandardResponse[dict])
async def admin_replay_event(
    request: Request,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Idempotent recovery: Replays a specific event from the EventOutbox by resetting its status.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    service = ReplayService(db)
    
    await service.replay_event(event_id, current_user.email)
    
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "event_id": event_id,
            "status": "success",
            "message": f"Successfully queued event {event_id} for replay.",
        },
    )

@router.post("/replay/failed", response_model=StandardResponse[dict])
async def admin_replay_failed_batch(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Idempotent recovery: Batch replays all events currently marked as FAILED or DEAD_LETTER.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    service = ReplayService(db)
    
    count = await service.replay_failed_batch(current_user.email)
    
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "replayed_count": count,
            "status": "success",
            "message": f"Successfully queued {count} failed events for batch replay.",
        },
    )

# ---------------------------------------------------------------------------
# 5. Root Cause Explorer (Ledger & Timeline)
# ---------------------------------------------------------------------------
from app.models.telemetry import TimelineNode

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

@router.post("/articles/{id}/rollback/{revision_number}", response_model=StandardResponse[dict])
async def rollback_processed_article(
    request: Request,
    id: int,
    revision_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("editor", "admin", "super_admin")),
):
    """
    Rollback an article to a specific historical revision number.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    # 1. Fetch the target article
    stmt = select(ProcessedArticle).where(ProcessedArticle.id == id)
    res = await db.execute(stmt)
    article = res.scalars().first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Article ID {id} not found.")

    # 2. Fetch the target revision
    rev_stmt = select(ArticleRevision).where(
        ArticleRevision.article_id == id, ArticleRevision.revision_number == revision_number
    )
    rev_res = await db.execute(rev_stmt)
    revision = rev_res.scalars().first()
    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Revision #{revision_number} for Article ID {id} not found."
        )

    # 3. Enforce permissions: Editors can only rollback to revisions they personally created (revision.user_id == current_user.id)
    if current_user.role.name == "editor":
        if revision.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Editors can only rollback to revisions they personally created.",
            )

    # 4. Fetch max existing revision_number to create a new revision before applying rollback
    max_rev_stmt = select(func.max(ArticleRevision.revision_number)).where(ArticleRevision.article_id == id)
    max_rev_res = await db.execute(max_rev_stmt)
    max_rev = max_rev_res.scalar() or 0
    next_rev = max_rev + 1

    # 5. Create a new ArticleRevision representing the pre-rollback state so rollbacks are reversible
    pre_rollback_revision = ArticleRevision(
        article_id=article.id,
        user_id=current_user.id,
        title=article.title,
        summary=article.summary,
        tags=article.tags,
        content=article.content,
        revision_number=next_rev,
    )
    db.add(pre_rollback_revision)

    # 6. Apply the rollback values
    article.title = revision.title
    article.summary = revision.summary
    article.tags = revision.tags
    article.content = revision.content

    # Recompute slug
    import re

    slug = revision.title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    base_slug = slug
    suffix = 1
    while True:
        dup_stmt = select(ProcessedArticle).where(ProcessedArticle.slug == slug, ProcessedArticle.id != id)
        dup_res = await db.execute(dup_stmt)
        if not dup_res.scalars().first():
            break
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    article.slug = slug

    await db.commit()

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="ROLLBACK_ARTICLE",
        resource=f"article:{article.id}",
        metadata={"rolled_back_to_revision": revision_number, "new_revision_created": next_rev, "title": article.title},
        ip_address=ip,
    )
    await db.commit()

    logger.info(f"Admin: Article ID {article.id} rolled back to revision {revision_number} by {current_user.email}.")
    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "article_id": article.id,
            "rolled_back_to": revision_number,
            "new_revision_number": next_rev,
            "message": f"Successfully rolled back article to revision #{revision_number}.",
        },
    )


# ---------------------------------------------------------------------------
# 4. RBAC & User Management
# ---------------------------------------------------------------------------


@router.get("/users", response_model=StandardResponse[list])
async def list_platform_users(
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Retrieve all registered user accounts with associated role mapping.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(User).options(selectinload(User.role)).order_by(User.id.asc())
    if q:
        search_pattern = f"%{q}%"
        stmt = stmt.where((User.name.ilike(search_pattern)) | (User.email.ilike(search_pattern)))
    result = await db.execute(stmt)
    users = result.scalars().all()

    return StandardResponse(
        correlation_id=correlation_id,
        data=[
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role.name if u.role else None,
                "status": u.status,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    )


@router.put("/users/{id}/role", response_model=StandardResponse[dict])
async def update_user_role(
    request: Request,
    id: int,
    payload: UserRoleUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """
    Modify user authorization role. Promotes/demotes user capabilities.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    # 1. Fetch user to update
    user_stmt = select(User).options(selectinload(User.role)).where(User.id == id)
    user_res = await db.execute(user_stmt)
    target_user = user_res.scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User ID {id} not found.")

    # 2. Fetch role mapping
    role_stmt = select(Role).where(Role.name == payload.role)
    role_res = await db.execute(role_stmt)
    target_role = role_res.scalars().first()
    if not target_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{payload.role}' does not exist.")

    # Prevent demoting the last super admin
    if target_user.role and target_user.role.name == "super_admin" and payload.role != "super_admin":
        count_stmt = select(func.count(User.id)).join(Role).where(Role.name == "super_admin")
        super_count = (await db.execute(count_stmt)).scalar() or 0
        if super_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote the last super_admin account."
            )

    old_role = target_user.role.name if target_user.role else "none"
    target_user.role_id = target_role.id

    # 3. Log audit event and flush
    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="UPDATE_USER_ROLE",
        resource=f"user:{target_user.id}",
        metadata={"email": target_user.email, "old_role": old_role, "new_role": payload.role},
        ip_address=ip,
    )

    # 4. Wipe cached permissions to force recalculation on next API access
    try:
        from app.core.security import clear_permission_cache

        await clear_permission_cache(target_user.id)
    except Exception as e:
        logger.warning(f"Failed to clear permission cache: {e}")

    await db.commit()

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "user_id": target_user.id,
            "email": target_user.email,
            "role": payload.role,
            "message": f"Successfully updated role for user '{target_user.email}' from '{old_role}' to '{payload.role}'.",
        },
    )


@router.put("/users/{id}/status", response_model=StandardResponse[dict])
async def update_user_status(
    request: Request,
    id: int,
    payload: UserStatusUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Disable or suspend a user account.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    target_status = payload.status.lower()

    if target_status not in ["active", "disabled", "suspended"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status option.")

    stmt = select(User).options(selectinload(User.role)).where(User.id == id)
    res = await db.execute(stmt)
    target_user = res.scalars().first()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User ID {id} not found.")

    # Prevent normal admins from disabling or suspending other admins or super admins
    if current_user.role.name == "admin":
        if target_user.role and target_user.role.name in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators cannot suspend or deactivate other administrators or super administrators.",
            )

    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable or suspend your own account."
        )

    # Prevent disabling the last super admin
    if target_user.role and target_user.role.name == "super_admin" and target_status != "active":
        count_stmt = select(func.count(User.id)).join(Role).where(Role.name == "super_admin")
        super_count = (await db.execute(count_stmt)).scalar() or 0
        if super_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot disable or suspend the last super_admin account.",
            )

    old_status = target_user.status
    target_user.status = target_status

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="UPDATE_USER_STATUS",
        resource=f"user:{target_user.id}",
        metadata={"email": target_user.email, "old_status": old_status, "new_status": target_status},
        ip_address=ip,
    )

    # Forcefully invalidate any active sessions or permission caches
    try:
        from app.core.security import clear_permission_cache

        await clear_permission_cache(target_user.id)
    except Exception as e:
        logger.warning(f"Failed to clear permission cache: {e}")

    await db.commit()

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "user_id": target_user.id,
            "email": target_user.email,
            "status": target_status,
            "message": f"Successfully updated status for user '{target_user.email}' from '{old_status}' to '{target_status}'.",
        },
    )


# ---------------------------------------------------------------------------
# 5. Audit Logging Operations
# ---------------------------------------------------------------------------


@router.get("/audit-logs", response_model=PaginatedResponse[dict])
async def fetch_audit_logs(
    limit: int = 50,
    cursor: int | None = None,
    action_filter: str | None = None,
    user_filter: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Fetch comprehensive historical audit log entries, supporting Cursor-based pagination and filtering.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    stmt = select(AuditLog).options(selectinload(AuditLog.user)).order_by(AuditLog.id.desc()).limit(limit + 1)

    if cursor:
        stmt = stmt.where(AuditLog.id < cursor)
    if action_filter:
        stmt = stmt.where(AuditLog.action == action_filter)
    if user_filter:
        val = user_filter.strip()
        if val.isdigit():
            stmt = stmt.where(AuditLog.user_id == int(val))
        else:
            user_stmt = select(User.id).where(User.email.ilike(f"%{val}%"))
            res = await db.execute(user_stmt)
            uids = res.scalars().all()
            if uids:
                stmt = stmt.where(AuditLog.user_id.in_(uids))
            else:
                stmt = stmt.where(AuditLog.user_id == -1)
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = stmt.where(AuditLog.created_at >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
            stmt = stmt.where(AuditLog.created_at <= ed)
        except ValueError:
            pass

    res = await db.execute(stmt)
    logs = res.scalars().all()

    has_more = len(logs) > limit
    logs_slice = logs[:limit]

    next_cursor = str(logs_slice[-1].id) if has_more and logs_slice else None

    return PaginatedResponse(
        correlation_id=correlation_id,
        data=[
            {
                "id": l.id,
                "user_id": l.user_id,
                "user_email": l.user.email if l.user else "System",
                "action": l.action,
                "resource": l.resource,
                "metadata": l.metadata_,
                "ip_address": l.ip_address,
                "device": l.device,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs_slice
        ],
        pagination=PaginationMetadata(next_cursor=next_cursor, has_more=has_more, limit=limit),
    )


# ---------------------------------------------------------------------------
# 6. AI Ingestion Queue & Costs Controls
# ---------------------------------------------------------------------------


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


@router.post("/ai/replay/{id}", response_model=StandardResponse[dict])
async def replay_ai_job(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Replay a failed or dead_letter AI job by resetting its status to ai_queued and clearing error metadata.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    from app.models.article import RawArticle

    stmt = select(RawArticle).where(RawArticle.id == id)
    res = await db.execute(stmt)
    raw_article = res.scalars().first()

    if not raw_article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"RawArticle ID {id} not found.")

    if raw_article.status not in ["failed", "dead_letter"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot replay article in status {raw_article.status}"
        )

    # Reset metadata
    raw_article.status = "ai_queued"
    raw_article.retry_count = 0
    raw_article.last_retry_at = None
    raw_article.processing_started_at = None
    raw_article.error_log = None
    raw_article.dead_letter_reason = None
    raw_article.dead_letter_at = None

    from app.models.user import AuditLog

    audit_log = AuditLog(
        user_id=current_user.id,
        action="replay_requested",
        resource="RawArticle",
        metadata_={"raw_article_id": raw_article.id, "reason": "Admin requested manual replay of failed/dead AI job."},
    )
    db.add(audit_log)

    await db.commit()

    # Re-queue the task
    from celery_app import process_raw_article_task

    process_raw_article_task.delay(raw_article.id)

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "raw_article_id": raw_article.id,
            "status": "success",
            "message": "Job successfully reset and re-queued for AI summarization.",
        },
    )


from pydantic import BaseModel


class AITestRequest(BaseModel):
    prompt_version: str
    model: str
    text: str


@router.post("/ai/test", response_model=StandardResponse[dict])
async def test_ai_prompt(
    payload: AITestRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "super_admin")),
):
    """
    Test an AI prompt with a given model and input text, returning the raw provider payload.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    from app.ai.providers.factory import build_ai_provider
    from app.ai.schemas import AITaskRequest, AITaskType, ArticleAIInput
    from app.ai.service import AIService

    service = AIService()
    try:
        prompt, prompt_hash = service.prompt_registry.get_prompt(payload.prompt_version)

        request = AITaskRequest(
            task_type=AITaskType.SUMMARY,
            article=ArticleAIInput(title="Test Article", content=payload.text),
            prompt=prompt,
            prompt_version=payload.prompt_version,
            prompt_hash=prompt_hash,
            model=payload.model,
            max_output_tokens=1000,
        )

        # Build provider based on settings or default to openai for testing
        from app.core.config import settings

        primary_provider = settings.AI_PROVIDER_PRIORITY.split(",")[0]
        provider = build_ai_provider(primary_provider)

        ai_response = await service._dispatch(provider, request)

        return StandardResponse(
            correlation_id=correlation_id,
            data={
                "status": "success",
                "raw_response": ai_response.model_dump(),
                "system_prompt": request.prompt,
                "user_prompt": request.article.content,
                "prompt_version": payload.prompt_version,
                "model": payload.model,
            },
        )
    except Exception as e:
        return StandardResponse(
            correlation_id=correlation_id,
            data={
                "status": "error",
                "message": str(e),
                "prompt_version": payload.prompt_version,
                "model": payload.model,
            },
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


@router.get("/feature-flags", response_model=StandardResponse[list])
async def list_system_feature_flags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """
    Fetch all active configuration feature flags.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    stmt = select(FeatureFlag).order_by(FeatureFlag.key.asc())
    res = await db.execute(stmt)
    flags = res.scalars().all()

    return StandardResponse(
        correlation_id=correlation_id,
        data=[
            {
                "id": f.id,
                "name": f.key,
                "enabled": f.default_value,
                "description": f.description,
                "updated_at": f.updated_at.isoformat(),
            }
            for f in flags
        ],
    )


@router.post("/feature-flags/{name}/toggle", response_model=StandardResponse[dict])
async def toggle_system_feature_flag(
    request: Request,
    name: str,
    payload: FeatureFlagToggle = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
    """
    Enable or disable system operational parameters dynamically via feature flags.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    stmt = select(FeatureFlag).where(FeatureFlag.key == name)
    res = await db.execute(stmt)
    flag = res.scalars().first()

    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Feature flag '{name}' not found.")

    old_state = flag.default_value
    flag.default_value = payload.enabled

    # Also update production environment for immediate effect
    states = dict(flag.environment_states) if flag.environment_states else {}
    states["production"] = payload.enabled
    flag.environment_states = states

    flag.updated_at = datetime.now(timezone.utc)

    ip = request.client.host if request and request.client else "unknown"
    await log_audit(
        db=db,
        user_id=current_user.id,
        action="TOGGLE_FEATURE_FLAG",
        resource=f"flag:{name}",
        metadata={"flag": name, "old_state": old_state, "new_state": flag.default_value},
        ip_address=ip,
    )
    await db.commit()

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "flag": name,
            "enabled": flag.default_value,
            "message": f"Successfully toggled feature flag '{name}' to {flag.default_value}.",
        },
    )


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
