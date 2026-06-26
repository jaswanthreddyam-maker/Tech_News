from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import require_permission
from app.models.distribution import DistributionJob, DistributionManifest
from app.models.user import User
from app.schemas.distribution import DistributionJobResponse, DistributionManifestResponse

router = APIRouter()

@router.get("/manifests/{manifest_id}", response_model=DistributionManifestResponse)
async def get_distribution_manifest(
    manifest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.FULL_ADMIN)),
):
    stmt = select(DistributionManifest).options(
        selectinload(DistributionManifest.jobs).selectinload(DistributionJob.reports)
    ).where(DistributionManifest.id == manifest_id)
    res = await db.execute(stmt)
    manifest = res.scalars().first()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    return manifest

@router.get("/jobs/{job_id}", response_model=DistributionJobResponse)
async def get_distribution_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.FULL_ADMIN)),
):
    stmt = select(DistributionJob).options(selectinload(DistributionJob.reports)).where(DistributionJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
