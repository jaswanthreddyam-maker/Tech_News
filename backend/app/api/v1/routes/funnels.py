from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import require_permission
from app.growth.schemas import FunnelCreate, FunnelMetricsResponse, FunnelResponse
from app.models.growth import Funnel, FunnelMetrics, FunnelState, FunnelStep
from app.models.user import utc_now

router = APIRouter()

@router.post("/", response_model=FunnelResponse)
async def create_funnel(funnel_in: FunnelCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    funnel = Funnel(
        key=funnel_in.key,
        name=funnel_in.name,
        description=funnel_in.description,
        version=funnel_in.version,
        status=funnel_in.status,
        subject_type=funnel_in.subject_type,
        time_window_seconds=funnel_in.time_window_seconds
    )
    db.add(funnel)
    await db.flush()

    for step_in in funnel_in.steps:
        step = FunnelStep(
            funnel_id=funnel.id,
            step_order=step_in.step_order,
            name=step_in.name,
            event_matcher=step_in.event_matcher,
            is_optional=step_in.is_optional
        )
        db.add(step)

    await db.commit()
    await db.refresh(funnel)
    return funnel

@router.get("/", response_model=list[FunnelResponse])
async def list_funnels(db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    result = await db.execute(
        select(Funnel).options(selectinload(Funnel.steps))
    )
    return result.scalars().all()

@router.get("/{funnel_id}/metrics", response_model=list[FunnelMetricsResponse])
async def get_funnel_metrics(funnel_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    result = await db.execute(
        select(FunnelMetrics).where(FunnelMetrics.funnel_id == funnel_id)
    )
    return result.scalars().all()

@router.get("/{funnel_id}/state/{subject_id}")
async def get_funnel_state(funnel_id: int, subject_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    """Debugging endpoint to view subject progression in a funnel"""
    result = await db.execute(
        select(FunnelState).where(
            FunnelState.funnel_id == funnel_id,
            FunnelState.subject_id == subject_id
        )
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="FunnelState not found")

    return {
        "funnel_id": state.funnel_id,
        "subject_id": state.subject_id,
        "current_step_order": state.current_step_order,
        "is_completed": state.is_completed,
        "started_at": state.started_at,
        "entered_step_at": state.entered_step_at,
        "completed_at": state.completed_at,
        "expires_at": state.expires_at,
        "is_expired": (utc_now() > state.expires_at) if state.expires_at else False,
        "dimension_snapshot": state.dimension_snapshot
    }
