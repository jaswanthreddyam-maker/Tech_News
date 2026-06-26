import asyncio

from sqlalchemy import text

from app.core.database import async_engine


async def update_enum():
    async with async_engine.connect() as conn:
        # Commit to close transaction block before ALTER TYPE
        await conn.commit()
        await conn.execute(text("COMMIT"))
        for val in ['PENDING', 'VALIDATING', 'PREFLIGHT', 'RUNNING', 'SUCCEEDED']:
            try:
                # We execute each ALTER TYPE directly
                await conn.execute(text(f"ALTER TYPE distributionjobstatus ADD VALUE '{val}'"))
                print(f"Added {val}")
            except Exception as e:
                print(f"Failed {val}: {e}")
        await conn.commit()

asyncio.run(update_enum())
