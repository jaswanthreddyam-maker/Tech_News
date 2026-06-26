from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import require_permission
from app.growth.schemas import (
    CohortCreate,
    CohortMembershipResponse,
    CohortResponse,
    CohortSnapshotResponse,
    CohortStatsResponse,
)
from app.models.growth import Cohort, CohortMembership, CohortRule, CohortSnapshot
from app.models.user import utc_now

router = APIRouter()

@router.post("/", response_model=CohortResponse)
async def create_cohort(cohort_in: CohortCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    cohort = Cohort(
        key=cohort_in.key,
        name=cohort_in.name,
        description=cohort_in.description,
        version=cohort_in.version,
        status=cohort_in.status,
        subject_type=cohort_in.subject_type,
        refresh_mode=cohort_in.refresh_mode,
        parent_cohort_id=cohort_in.parent_cohort_id
    )
    db.add(cohort)
    await db.flush()

    for rule_in in cohort_in.rules:
        rule = CohortRule(
            cohort_id=cohort.id,
            rule_capability=rule_in.rule_capability,
            expression=rule_in.expression
        )
        db.add(rule)

    await db.commit()
    await db.refresh(cohort)
    return cohort

@router.get("/", response_model=list[CohortResponse])
async def list_cohorts(db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    result = await db.execute(select(Cohort))
    return result.scalars().all()

@router.get("/{cohort_id}/members", response_model=list[CohortMembershipResponse])
async def get_cohort_members(cohort_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    result = await db.execute(
        select(CohortMembership).where(
            CohortMembership.cohort_id == cohort_id,
            CohortMembership.status == "ENTERED"
        )
    )
    return result.scalars().all()

@router.post("/{cohort_id}/members")
async def add_manual_members(cohort_id: int, subject_ids: list[str], db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    cohort = await db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    if cohort.refresh_mode != "MANUAL":
        raise HTTPException(status_code=400, detail="Can only manually add members to MANUAL cohorts")

    now = utc_now()
    for subject_id in subject_ids:
        membership = CohortMembership(
            cohort_id=cohort.id,
            subject_id=subject_id,
            status="ENTERED",
            reason="Manual addition",
            cohort_version=cohort.version,
            rule_version="v1",
            projection_version=1,
            added_at=now
        )
        db.add(membership)

    await db.commit()
    return {"message": f"Added {len(subject_ids)} members"}

@router.get("/{cohort_id}/snapshots", response_model=list[CohortSnapshotResponse])
async def get_cohort_snapshots(cohort_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    result = await db.execute(
        select(CohortSnapshot).where(CohortSnapshot.cohort_id == cohort_id).order_by(CohortSnapshot.snapshot_time.desc())
    )
    return result.scalars().all()

@router.get("/{cohort_id}/stats", response_model=CohortStatsResponse)
async def get_cohort_stats(cohort_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    # Group by status to get real-time stats
    stmt = select(CohortMembership.status, func.count(CohortMembership.id)).where(CohortMembership.cohort_id == cohort_id).group_by(CohortMembership.status)
    result = await db.execute(stmt)

    stats = dict(result.all())

    active = stats.get("ENTERED", 0)
    paused = stats.get("PAUSED", 0)
    exited = stats.get("EXITED", 0)

    return CohortStatsResponse(
        cohort_id=cohort_id,
        total_members=active + paused + exited,
        active_members=active,
        paused_members=paused
    )
