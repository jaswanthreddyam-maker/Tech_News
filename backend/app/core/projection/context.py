from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar('T', bound=Base)

class ProjectionContext:
    """
    Read-only database wrapper for pure projectors.
    Projectors can load state to compute derived values but cannot mutate state.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def load(self, model: type[T], target: Any) -> T | None:
        """Load a single record by its primary key, a dict of conditions, or 'id'."""
        if isinstance(target, dict):
            stmt = select(model)
            for k, v in target.items():
                stmt = stmt.where(getattr(model, k) == v)
            return (await self.session.execute(stmt)).scalar_one_or_none()

        pk_col = next(iter(model.__table__.primary_key.columns))
        lookup_col = pk_col
        for col in model.__table__.columns:
            if target and isinstance(target, str) and col.name.endswith("_id") and col.name != "id":
                lookup_col = col
                break

        stmt = select(model).where(lookup_col == target)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def exists(self, model: type[T], target: Any) -> bool:
        obj = await self.load(model, target)
        return obj is not None

    async def query(self, stmt) -> Sequence[Any]:
        return (await self.session.execute(stmt)).scalars().all()

    async def aggregate(self, stmt) -> Any:
        return (await self.session.execute(stmt)).scalar()
