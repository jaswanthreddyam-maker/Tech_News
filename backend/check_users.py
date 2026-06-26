import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import (
    User,
)


async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User))
        users = res.scalars().all()
        for u in users:
            print(f"User: {u.email} | Hash: {u.password_hash} | Status: {u.status} | Role: {u.role_id}")


if __name__ == "__main__":
    asyncio.run(main())
