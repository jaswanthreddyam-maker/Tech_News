
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import get_current_user, require_permission
from app.growth.experiments import ExperimentEvaluationEngine
from app.growth.schemas import ExperimentResponse, ExperimentVariantResponse, FeatureFlagContext
from app.models.growth import Experiment
from app.models.user import User

router = APIRouter()

@router.post("/evaluate", response_model=dict[str, ExperimentVariantResponse | None])
async def evaluate_experiments(
    context: FeatureFlagContext,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evaluate all running experiments against the provided context.
    Returns a dictionary of experiment_key -> Variant (or None if not eligible/assigned).
    """
    # Fetch all running experiments with variants
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.variants))
        .where(Experiment.status == "RUNNING")
    )
    experiments = result.scalars().all()

    evaluations = {}
    for experiment in experiments:
        variant = await ExperimentEvaluationEngine.evaluate(experiment, context, db)
        evaluations[experiment.key] = variant

    # Commit the db session to persist assignments and flush Outbox events
    await db.commit()

    return evaluations

@router.get("/", response_model=list[ExperimentResponse])
async def list_experiments(db: AsyncSession = Depends(get_db), user: dict = Depends(require_permission(Permission.FULL_ADMIN))):
    """
    List all experiments (admin view).
    """
    result = await db.execute(
        select(Experiment).options(selectinload(Experiment.variants))
    )
    experiments = result.scalars().all()
    return experiments
