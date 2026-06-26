from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import get_current_user, require_permission
from app.growth.engine import GrowthEvaluationEngine
from app.growth.schemas import FeatureFlagContext, FeatureFlagEvaluation, FeatureFlagResponse
from app.models.growth import FeatureFlag
from app.models.user import User

router = APIRouter()

@router.post("/flags/evaluate", response_model=dict[str, FeatureFlagEvaluation])
async def evaluate_flags(
    context: FeatureFlagContext,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evaluate all active feature flags against the provided context.
    Returns a dictionary of flag_key -> FeatureFlagEvaluation.
    """
    # Fetch all flags
    result = await db.execute(select(FeatureFlag))
    flags = result.scalars().all()

    evaluations = {}
    for flag in flags:
        evaluation = await GrowthEvaluationEngine.evaluate(flag, context, db)
        evaluations[flag.key] = evaluation

    # Commit the db session to flush Outbox events
    await db.commit()

    return evaluations

@router.get("/flags", response_model=list[FeatureFlagResponse])
async def list_flags(db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    """
    List all feature flags (admin view).
    """
    result = await db.execute(select(FeatureFlag))
    flags = result.scalars().all()
    return flags
