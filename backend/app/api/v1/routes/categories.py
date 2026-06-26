from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.models.article import Category
from app.schemas.responses import StandardResponse

router = APIRouter()


@router.get("", response_model=StandardResponse[list])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """
    Fetch all active tech news categories from the PostgreSQL database.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    stmt = select(Category).order_by(Category.id.asc())
    result = await db.execute(stmt)
    categories = result.scalars().all()

    # Map ORM model instances to list of dicts
    categories_list = [{"id": cat.id, "name": cat.name, "slug": cat.slug} for cat in categories]

    return StandardResponse(correlation_id=correlation_id, data=categories_list)
