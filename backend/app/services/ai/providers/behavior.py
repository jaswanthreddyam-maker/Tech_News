
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavioral import UserInterest
from app.schemas.ai_context import ContextBehavior


class BehaviorProvider:
    async def get(self, session: AsyncSession, user_id: int | None, anonymous_id: str | None) -> ContextBehavior | None:
        if not user_id and not anonymous_id:
            return None

        stmt = select(UserInterest)
        if user_id:
            stmt = stmt.where(UserInterest.user_id == user_id)
        elif anonymous_id:
            stmt = stmt.where(UserInterest.anonymous_id == anonymous_id)

        stmt = stmt.order_by(desc(UserInterest.affinity)).limit(10)
        res = await session.execute(stmt)
        interests = res.scalars().all()

        if not interests:
            return None

        top_interests = [i.entity_id for i in interests if i.entity_type == "TOPIC"][:5]
        recent_categories = [i.entity_id for i in interests if i.entity_type == "CATEGORY"][:3]

        return ContextBehavior(
            top_interests=top_interests,
            recent_categories=recent_categories,
            reading_velocity_score=0.5, # Placeholder until we have session velocity
            expertise_level=0.0
        )
