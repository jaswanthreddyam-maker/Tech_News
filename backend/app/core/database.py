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
    "poolclass": NullPool,
    "connect_args": {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "command_timeout": 30,
    },
}

async_engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)

def configure_database_pool(pool_size: int = 2, max_overflow: int = 1):
    """Reconfigure database connection pool with NullPool by default for PgBouncer safety."""
    global async_engine
    configure_database_nullpool()


def configure_database_nullpool():
    """Use NullPool for Celery workers — no persistent connections.
    
    Each query creates a fresh connection and releases it immediately.
    This prevents connection accumulation across multiple forked workers
    that share a limited pgBouncer session-mode pool (e.g. Supabase 15-conn limit).
    """
    global async_engine
    if is_testing:
        return

    nullpool_kwargs = {
        "pool_pre_ping": True,
        "echo": False,
        "future": True,
        "poolclass": NullPool,
        "connect_args": {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "command_timeout": 30,  # Prevent slow queries from holding connections indefinitely
        },
    }
    new_engine = create_async_engine(settings.DATABASE_URL, **nullpool_kwargs)
    async_engine = new_engine
    AsyncSessionLocal.configure(bind=new_engine)
    logger.info("Database connection pool configured with NullPool (no persistent connections)")


# Dynamic Dependency Injection for API routes with connection burst resilience
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    for attempt in range(4):
        try:
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                    return
                except Exception as exc:
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                    err_str = str(exc)
                    if ("EMAXCONNSESSION" in err_str or "TooManyConnectionsError" in err_str or "connection limit" in err_str.lower() or "53300" in err_str) and attempt < 3:
                        logger.warning(f"Database session pool saturated (attempt {attempt+1}/4). Retrying in {(attempt+1)*0.2:.1f}s...")
                        await asyncio.sleep((attempt + 1) * 0.2)
                        continue
                    raise
        except Exception as exc:
            err_str = str(exc)
            if ("EMAXCONNSESSION" in err_str or "TooManyConnectionsError" in err_str or "connection limit" in err_str.lower() or "53300" in err_str) and attempt < 3:
                logger.warning(f"Database connection acquisition saturated (attempt {attempt+1}/4). Retrying in {(attempt+1)*0.2:.1f}s...")
                await asyncio.sleep((attempt + 1) * 0.2)
                continue
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
