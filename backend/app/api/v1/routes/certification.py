from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.certification import CertificationRun
from app.services.certification_service import CertificationService
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def submit_certification_run(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
    # Ideally protected by an API Key or strict service auth
):
    """Ingest a certification run from the External Runner."""
    service = CertificationService(db)
    try:
        run = await service.process_certification_run(payload)
        return {"id": str(run.id), "run_id": run.run_id, "grade": run.grade}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def get_certification_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the top-level certification status for the dashboard."""
    # Last Nightly Run
    stmt_nightly = (
        select(CertificationRun)
        .where(CertificationRun.certification_type == "NIGHTLY")
        .order_by(CertificationRun.completed_at.desc())
        .limit(5)
    )
    res_nightly = await db.execute(stmt_nightly)
    recent_runs = res_nightly.scalars().all()
    
    if not recent_runs:
        return {"status": "No runs yet", "grade": "N/A", "recent_runs": []}
        
    latest_run = recent_runs[0]
    
    runs_summary = []
    for r in recent_runs:
        runs_summary.append({
            "run_id": r.run_id,
            "type": r.certification_type,
            "passed": r.passed,
            "failed": r.failed,
            "grade": r.grade,
            "completed_at": r.completed_at.isoformat()
        })
        
    # Calculate simple pass rate of the latest run
    pass_rate = 0
    if latest_run.total_scenarios > 0:
        pass_rate = round((latest_run.passed / latest_run.total_scenarios) * 100)
        
    return {
        "last_run": latest_run.completed_at.isoformat(),
        "type": latest_run.certification_type,
        "grade": latest_run.grade,
        "pass_rate": pass_rate,
        "recent_runs": runs_summary
    }

@router.get("/runs")
async def get_certification_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(CertificationRun).order_by(CertificationRun.completed_at.desc()).limit(limit)
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [{"run_id": r.run_id, "grade": r.grade, "completed_at": r.completed_at.isoformat()} for r in runs]
