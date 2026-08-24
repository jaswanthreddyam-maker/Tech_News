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

def import_all_models():
    """Ensures all SQLAlchemy model mappers are registered before executing queries."""
    import importlib
    model_names = [
        "ai_artifacts", "analytics", "article", "behavioral", "certification",
        "conversation", "distribution", "editorial", "event", "growth",
        "intelligence", "knowledge", "memory", "recipient", "recommendation",
        "research", "source", "followed_source", "story", "telemetry", "tnt_knowledge",
        "user", "user_settings", "workspace"
    ]
    for name in model_names:
        try:
            importlib.import_module(f"app.models.{name}")
        except Exception as e:
            logger.warning(f"Could not import model {name}: {e}")
    try:
        importlib.import_module("app.briefing.models")
    except Exception as e:
        logger.warning(f"Could not import briefing models: {e}")

import_all_models()

from sqlalchemy.pool import NullPool

is_testing = os.getenv("USE_NULL_POOL", "0") == "1" or "pytest" in sys.modules

engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False,
    "future": True,
    "connect_args": {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
}

if is_testing:
    engine_kwargs["poolclass"] = NullPool
# Default fallback (e.g. for CLI or Beat) is highly restricted
if not is_testing:
    engine_kwargs.update({
        "pool_size": getattr(settings, "DB_POOL_SIZE", 3),
        "max_overflow": getattr(settings, "DB_MAX_OVERFLOW", 2),
        "pool_timeout": 30.0,
        "pool_recycle": 1800,
    })

async_engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)

def configure_database_pool(pool_size: int, max_overflow: int):
    """Explicitly reconfigure the connection pool for the current process."""
    global async_engine
    if is_testing:
        return
        
    engine_kwargs.update({
        "pool_size": pool_size,
        "max_overflow": max_overflow,
    })
    
    new_engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)
    async_engine = new_engine
    AsyncSessionLocal.configure(bind=new_engine)
    logger.info(f"Database connection pool configured with pool_size={pool_size}, max_overflow={max_overflow}")


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
