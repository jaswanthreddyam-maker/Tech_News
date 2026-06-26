import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.behavioral import UserInterest
from app.services.behavioral.profiler import ProfileUpdater

logging.basicConfig(level=logging.INFO)


async def main():
    async with AsyncSessionLocal() as db:
        # We assume there is at least one session in the db
        from app.models.behavioral import ReadingSession

        res = await db.execute(select(ReadingSession).limit(1))
        session = res.scalar_one_or_none()

        if not session:
            print("No sessions found to profile.")
            return

        print(f"Running profile updater for anon={session.anonymous_id}, user={session.user_id}")

        updater = ProfileUpdater(db)
        await updater.update_profile_for_user(user_id=session.user_id, anonymous_id=session.anonymous_id)

        res = await db.execute(
            select(UserInterest).where(
                (UserInterest.user_id == session.user_id) | (UserInterest.anonymous_id == session.anonymous_id)
            )
        )
        interests = res.scalars().all()

        print(f"Generated {len(interests)} interests!")
        for i in interests:
            print(f"- {i.entity_type} {i.entity_id}: score={i.score:.2f}, conf={i.confidence:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
