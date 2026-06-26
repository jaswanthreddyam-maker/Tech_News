import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

# We use an in-memory SQLite to simulate the engine pooling without needing postgres
async_engine = create_async_engine("sqlite+aiosqlite:///:memory:", pool_size=5, max_overflow=10)

def simulate_celery_task():
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
        print(f"[CELERY WORKER TASK] asyncio.get_running_loop() ID = {loop_id}")

        print("[CELERY WORKER TASK] Attempting to connect via global engine...")
        try:
            # When we try to acquire a connection from the global engine that was initialized in another loop
            async with async_engine.connect() as conn:
                print("[CELERY WORKER TASK] SUCCESS")
        except Exception as e:
            print(f"[CELERY WORKER TASK] ERROR: {type(e).__name__}: {e}")

    loop.run_until_complete(_execute())

if __name__ == "__main__":
    async def global_init():
        print(f"[MAIN PROCESS] Initializing Global Engine in Loop ID = {id(asyncio.get_running_loop())}")
        # Force the engine pool to initialize a connection in this loop
        async with async_engine.connect() as conn:
            pass

    asyncio.run(global_init())

    print("\n--- Simulating Celery Worker picking up a task (new loop) ---\n")
    simulate_celery_task()
