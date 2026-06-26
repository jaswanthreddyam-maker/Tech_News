import re

with open("c:/Users/HP/Downloads/tech_news/backend/celery_app.py") as f:
    content = f.read()

# 1. Insert worker_process_init and helper at the top (after imports and celery_app initialization, before beat schedule)
insert_text = """
import asyncio
from celery.signals import worker_process_init
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

celery_engine = None
CeleryAsyncSessionLocal = None
worker_loop = None

@worker_process_init.connect
def init_worker_process(**kwargs):
    global celery_engine, CeleryAsyncSessionLocal, worker_loop
    
    # Create persistent event loop for this worker process
    worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)
    
    # Initialize the engine bound to this worker's loop
    celery_engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
    )
    CeleryAsyncSessionLocal = sessionmaker(
        bind=celery_engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("Celery worker process initialized with process-local isolated async_engine and loop.")

def run_in_worker_loop(coro):
    \"\"\"Helper to safely run coroutines using the persistent worker loop, or fallback to a new one.\"\"\"
    global worker_loop
    if worker_loop and not worker_loop.is_closed():
        return worker_loop.run_until_complete(coro)
    else:
        # Fallback for sync execution contexts (e.g., tests or eager mode)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

def get_celery_session():
    \"\"\"Returns the worker-local session maker, or global if not in a worker.\"\"\"
    global CeleryAsyncSessionLocal
    if CeleryAsyncSessionLocal:
        return CeleryAsyncSessionLocal()
    from app.core.database import AsyncSessionLocal
    return AsyncSessionLocal()

"""

content = content.replace("celery_app.conf.update(", insert_text + "celery_app.conf.update(")

# 2. Replace the boilerplate try-except loop blocks
loop_pattern_1 = re.compile(r"    try:\n\s*loop = asyncio\.get_event_loop\(\)\n\s*if loop\.is_closed\(\):\n\s*loop = asyncio\.new_event_loop\(\)\n\s*asyncio\.set_event_loop\(loop\)\n\s*except RuntimeError:\n\s*loop = asyncio\.new_event_loop\(\)\n\s*asyncio\.set_event_loop\(loop\)\n")
loop_pattern_2 = re.compile(r"    try:\n\s*loop = asyncio\.get_event_loop\(\)\n\s*except RuntimeError:\n\s*loop = asyncio\.new_event_loop\(\)\n\s*asyncio\.set_event_loop\(loop\)\n")

content = loop_pattern_1.sub("", content)
content = loop_pattern_2.sub("", content)

# 3. Replace loop.run_until_complete(_execute()) with run_in_worker_loop(_execute())
content = re.compile(r"loop\.run_until_complete\((.*?)\)").sub(r"run_in_worker_loop(\1)", content)

# 4. Replace `from app.core.database import AsyncSessionLocal` with use of `get_celery_session()`
# Wait, let's just replace `async with AsyncSessionLocal() as db:` with `async with get_celery_session() as db:`
content = content.replace("async with AsyncSessionLocal() as db:", "async with get_celery_session() as db:")
# Remove unused imports of AsyncSessionLocal
content = content.replace("    from app.core.database import AsyncSessionLocal\n", "")

with open("c:/Users/HP/Downloads/tech_news/backend/celery_app.py", "w") as f:
    f.write(content)

print("Updated celery_app.py")
