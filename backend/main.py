import logging
import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

mimetypes.add_type("image/webp", ".webp")

from app.api.v1.router import api_router
from app.api.v1.routes import (
    chat,
)
from app.core.config import settings
from app.core.database import async_engine, verify_database_connection, get_db

from app.core.logging import LoggingMiddleware, correlation_id_ctx, setup_logging
from app.core.middleware import MaintenanceModeMiddleware
from app.core.redis import close_redis_connection, verify_redis_connection
from app.schemas.responses import ErrorDetails, ErrorResponse

# Setup rotating files and console formatting
setup_logging(env=settings.ENV)
logger = logging.getLogger("tech_news.main")


# 1. Modern FastAPI Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing multi-container startup checks...")

    # Register signal handlers for graceful shutdown of streams on reload/SIGTERM
    try:
        from app.core.shutdown import register_signal_handlers

        register_signal_handlers()
    except Exception as e:
        logger.warning(f"Failed to register signal handlers during lifespan setup: {e}")

    # Configure FastAPI database connection pool limits
    from app.core.database import configure_database_pool
    configure_database_pool(pool_size=10, max_overflow=10)

    # Verify strict PostgreSQL connection
    db_ok = await verify_database_connection(max_retries=5, initial_delay=1.0)
    if not db_ok:
        logger.critical("Database connection validation failed! Shutting down.")
        raise RuntimeError("PostgreSQL database unavailable.")

    # Verify Redis connection
    redis_ok = await verify_redis_connection()
    if not redis_ok:
        logger.warning("Redis connection validation failed. Cache services compromised.")

    # Initialize OpenTelemetry distributed tracing
    try:
        from app.core.tracing import init_tracing
        init_tracing()
    except Exception as e:
        logger.warning(f"OpenTelemetry initialization failed (non-fatal): {e}")

    # 1.1 Auto-run Alembic schema migrations & seed canonical sources
    try:
        import subprocess
        import os

        ini_path = os.path.join(os.getcwd(), "alembic.ini")
        if os.path.exists(ini_path):
            mig_res = subprocess.run(
                ["alembic", "-c", ini_path, "upgrade", "head"],
                capture_output=True,
                text=True,
            )
            if mig_res.returncode == 0:
                logger.info(f"Alembic startup migration success: {mig_res.stdout.strip()}")
            else:
                logger.warning(f"Alembic startup migration stderr: {mig_res.stderr.strip()}")
        else:
            logger.warning(f"alembic.ini not found at {ini_path}")
    except Exception as mig_err:
        logger.warning(f"Startup migration runner notice: {mig_err}")

    try:
        from app.core.init_db import main as init_db_main
        await init_db_main()
        logger.info("Canonical database initialization & sources synced.")
    except Exception as e:
        logger.warning(f"Startup init_db notice: {e}")

    # Run startup reconciliation and projection refresh
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.ranking.news_ranking_engine import expire_articles
        from app.editorial.homepage_builder import HomepageBuilder
        from app.services.cache_service import CacheService
        from app.services.ingestion.replenishment import AutoReplenishmentService

        logger.info("Running startup article expiration and projection reconciliation...")
        async with AsyncSessionLocal() as db:
            metrics = await expire_articles(db)
            if metrics.get("expired_articles_total", 0) > 0:
                logger.info(f"Startup reconciliation expired articles. Metrics: {metrics}")
            await HomepageBuilder.build_and_persist_homepage_projection(db)
            await HomepageBuilder.build_and_persist_category_desks(db)
            await CacheService.invalidate_homepage_cache(reason="startup_reconciliation")
            await AutoReplenishmentService.trigger_replenishment_if_needed(db)
    except Exception as e:
        logger.warning(f"Startup reconciliation failed: {e}")

    logger.info("Startup complete. System is healthy and accepting routes.")

    # Emit RECOVERY event on successful startup
    try:
        from app.core.event_bus import publish_event

        await publish_event("RECOVERY", "Newsroom core engine successfully restored.", "success")
    except Exception as e:
        logger.warning(f"Lifespan: Failed to emit RECOVERY event: {e}")

    # ── Autonomous Article Lifecycle & Replenishment Background Worker Loop ──
    from app.core.shutdown import shutdown_event
    import asyncio

    async def _autonomous_lifecycle_loop():
        """
        Autonomous background lifecycle worker (ticks every 60 seconds).
        Continuously expires aged articles, checks inventory levels, triggers
        auto-replenishment crawls, and rebuilds projections & category desks.
        """
        logger.info("Autonomous article lifecycle loop started.")
        while not shutdown_event.is_set():
            try:
                await asyncio.sleep(60)
                if shutdown_event.is_set():
                    break

                from app.core.database import AsyncSessionLocal
                from app.services.ranking.news_ranking_engine import expire_articles
                from app.editorial.homepage_builder import HomepageBuilder
                from app.services.cache_service import CacheService
                from app.services.ingestion.replenishment import AutoReplenishmentService

                async with AsyncSessionLocal() as db:
                    metrics = await expire_articles(db)
                    expired_count = metrics.get("expired_articles_total", 0)
                    if expired_count > 0:
                        logger.info(f"Lifecycle loop: Expired {expired_count} articles. Rebuilding projections.")
                        await HomepageBuilder.build_and_persist_homepage_projection(db)
                        await HomepageBuilder.build_and_persist_category_desks(db)
                        await CacheService.invalidate_homepage_cache(reason=f"periodic_expired_{expired_count}_articles")

                    repl_res = await AutoReplenishmentService.trigger_replenishment_if_needed(db)
                    if repl_res.get("triggered"):
                        logger.info(f"Lifecycle loop: AutoReplenishment executed: {repl_res}")

            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                logger.warning(f"Lifecycle loop encountered error: {loop_err}")

    lifecycle_task = asyncio.create_task(_autonomous_lifecycle_loop())

    yield  # Hand over execution to FastAPI

    # Notify active SSE connections and background tasks to close gracefully
    shutdown_event.set()
    if lifecycle_task and not lifecycle_task.done():
        lifecycle_task.cancel()
        try:
            await lifecycle_task
        except asyncio.CancelledError:
            pass

    logger.info("Shutting down API gateway container...")
    # Close database pool connections cleanly
    await async_engine.dispose()
    logger.info("PostgreSQL engine connections cleanly disposed.")
    # Close Redis client pool connections cleanly
    await close_redis_connection()
    logger.info("API gateway shutdown complete.")


# Instantiate FastAPI application using the Lifespan Handler
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous AI-driven Technology Newsroom Server",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# 2.5 CORS Origins List
cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://tech-news-alpha-eosin.vercel.app",
]
if isinstance(settings.BACKEND_CORS_ORIGINS, list):
    for o in settings.BACKEND_CORS_ORIGINS:
        if isinstance(o, str) and o.strip():
            clean_o = o.strip().rstrip("/")
            if clean_o not in cors_origins:
                cors_origins.append(clean_o)


def _get_cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    headers = {}
    if origin and (
        origin in cors_origins
        or origin.endswith(".vercel.app")
        or "localhost" in origin
        or "127.0.0.1" in origin
    ):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"
    return headers


# 2. Centralized Exception Handling Middleware
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    correlation_id = correlation_id_ctx.get() or "system"
    logger.warning(f"Request validation failed: {exc!s}")
    error_details = ErrorDetails(
        code="VALIDATION_ERROR",
        message="Request payload failed structured schema validation checks.",
        fields=exc.errors(),
    )
    response_content = ErrorResponse(correlation_id=correlation_id, error=error_details)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_content.model_dump(mode="json"),
        headers=_get_cors_headers(request),
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    correlation_id = correlation_id_ctx.get() or "system"
    logger.error(f"Database transaction failure: {exc!s}", exc_info=True)
    error_details = ErrorDetails(
        code="DATABASE_ERROR", message=f"A secure database transaction encountered an operational exception: {exc!s}"
    )
    response_content = ErrorResponse(correlation_id=correlation_id, error=error_details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_content.model_dump(mode="json"),
        headers=_get_cors_headers(request),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    correlation_id = correlation_id_ctx.get() or "system"
    logger.error(f"Unhandled server exception: {exc!s}", exc_info=True)
    error_details = ErrorDetails(
        code="INTERNAL_SERVER_ERROR",
        message=f"An unexpected server error occurred. {str(exc)}",
    )
    response_content = ErrorResponse(correlation_id=correlation_id, error=error_details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_content.model_dump(mode="json"),
        headers=_get_cors_headers(request),
    )


# 2.5 Mount Security Headers and CORS Middleware
from starlette.middleware.base import BaseHTTPMiddleware
if isinstance(settings.BACKEND_CORS_ORIGINS, list):
    for o in settings.BACKEND_CORS_ORIGINS:
        if isinstance(o, str) and o.strip():
            clean_o = o.strip().rstrip("/")
            if clean_o not in cors_origins:
                cors_origins.append(clean_o)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/uploads/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(MaintenanceModeMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Mount Static Uploads Folder
import os

from fastapi.staticfiles import StaticFiles

os.makedirs("/app/uploads/thumbnails", exist_ok=True)
app.mount("/api/v1/uploads", StaticFiles(directory="/app/uploads"), name="uploads")

# 6. Expose Prometheus Metrics Endpoint
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

@app.get("/metrics", tags=["System"])
async def metrics():
    """
    Prometheus metrics exporter.
    Scraped internally by Prometheus server.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# 7. Root Health Probes for Load Balancers / Railway
@app.get("/health/live", tags=["System"])
async def root_health_live():
    """Process-level liveness probe: returns 200 immediately with NO dependency calls."""
    return {"status": "healthy", "process": "alive", "service": "tech-news-today-backend"}

@app.get("/health", tags=["System"])
@app.get("/health/ready", tags=["System"])
async def root_health_ready(db=Depends(get_db)):
    """Application-level readiness probe: actively validates PostgreSQL & Redis connectivity."""
    postgres_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception as e:
        logger.error(f"Readiness probe: Postgres check failed: {e}")

    try:
        from app.core.redis import verify_redis_connection
        redis_ok = await verify_redis_connection()
    except Exception as e:
        logger.error(f"Readiness probe: Redis check failed: {e}")

    is_ready = postgres_ok and redis_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if is_ready else "unhealthy",
            "dependencies": {
                "postgres": "connected" if postgres_ok else "unreachable",
                "redis": "connected" if redis_ok else "unreachable",
            },
        },
    )


# 8. Mount Versioned Router Tree
api_router.include_router(chat.router)
app.include_router(api_router, prefix=settings.API_V1_STR)

