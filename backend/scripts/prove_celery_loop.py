import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import AsyncSessionLocal
from celery_app import celery_app


@celery_app.task(name="test_loop_identity")
def test_loop_identity():
    # Emulate the exact loop creation in Celery tasks
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def _execute():
        loop_id = id(asyncio.get_running_loop())
        print(f"[TEST] Inside Celery Task _execute(): asyncio.get_running_loop() ID = {loop_id}")

        async with AsyncSessionLocal() as db:
            print("[TEST] Inside AsyncSessionLocal(): Session created.")
            try:
                from sqlalchemy import text
                await db.execute(text("SELECT 1"))
                print("[TEST] db.execute() succeeded.")
            except Exception as e:
                print(f"[TEST] db.execute() failed: {e}")

    loop.run_until_complete(_execute())

if __name__ == "__main__":
    # Simulate a loop running before celery fork, e.g., the global import loop
    async def global_init():
        print(f"[TEST] Global init loop ID = {id(asyncio.get_running_loop())}")
        # Force the engine pool to initialize a connection in this loop
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))

    asyncio.run(global_init())

    print("Running Celery task which sets its own loop...")
    test_loop_identity.apply()
