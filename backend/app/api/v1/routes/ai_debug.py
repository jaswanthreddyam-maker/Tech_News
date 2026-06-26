import logging

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import require_permission
from app.schemas.ai_context import AIContext, PrivacyLevel
from app.schemas.responses import StandardResponse
from app.services.ai.context_builder import AIContextBuilder

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/context/{article_id}", response_model=StandardResponse[AIContext])
async def get_ai_context(
    article_id: int = Path(..., description="ID of the article"),
    privacy_level: PrivacyLevel = Query(PrivacyLevel.PUBLIC, description="Privacy level for context assembly"),
    user_id: int = Query(None, description="Optional user ID"),
    anonymous_id: str = Query(None, description="Optional anonymous ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FULL_ADMIN))
):
    """
    [Admin/Editor Only] Fetches the assembled AIContext for a given article and user configuration.
    This simulates what the LLM will see before generating summaries or insights.
    """

    logger.info(f"Building AI Context for article={article_id}, privacy={privacy_level}")
    builder = AIContextBuilder()
    context = await builder.build(
        session=db,
        article_id=article_id,
        privacy_level=privacy_level,
        user_id=user_id,
        anonymous_id=anonymous_id
    )

    return StandardResponse(correlation_id="debug", data=context)
