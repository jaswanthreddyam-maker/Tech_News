import asyncio
import logging
import time
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger("tech_news.database")

# Create Async Engine exclusively for PostgreSQL using asyncpg
# pool_pre_ping: Checks if connection is alive before serving a query
# pool_timeout: How long to wait for a connection from the pool before throwing a timeout
# pool_recycle: Recycles connections older than 30 minutes to prevent stale connections
import os
import sys

from sqlalchemy.pool import NullPool

is_testing = os.getenv("USE_NULL_POOL", "0") == "1" or "pytest" in sys.modules

engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False,
    "future": True,
}

if is_testing:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 15.0,
        "pool_recycle": 1800,
    })

async_engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)


# Dynamic Dependency Injection for API routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Startup verification helper with exponential retry logic and precise latency measurement
async def verify_database_connection(max_retries: int = 5, initial_delay: float = 1.0) -> bool:
    logger.info("Initializing PostgreSQL database startup checks...")
    delay = initial_delay
    start_time = time.time()

    for attempt in range(1, max_retries + 1):
        attempt_start = time.time()
        try:
            async with AsyncSessionLocal() as session:
                # Issue basic SELECT 1 to verify database responsiveness with 10s timeout
                await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=10.0)
                elapsed = (time.time() - start_time) * 1000
                attempt_elapsed = (time.time() - attempt_start) * 1000
                logger.info(
                    f"PostgreSQL database connection successfully verified on attempt {attempt}! "
                    f"Attempt Latency: {attempt_elapsed:.2f}ms. Total Startup Check Latency: {elapsed:.2f}ms."
                )
                return True
        except (asyncio.TimeoutError, Exception) as e:
            err_msg = "timed out after 10 seconds" if isinstance(e, asyncio.TimeoutError) else str(e)
            logger.warning(
                f"PostgreSQL connection attempt {attempt}/{max_retries} failed. Retrying in {delay}s. Error: {err_msg}"
            )
            if attempt == max_retries:
                logger.critical("Maximum PostgreSQL database connection attempts exceeded. Halting.")
                return False
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff

    return False
