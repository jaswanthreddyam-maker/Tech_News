import logging
import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

mimetypes.add_type("image/webp", ".webp")

from app.api.v1.router import api_router
from app.api.v1.routes import (
    chat,
)
from app.core.config import settings
from app.core.database import async_engine, verify_database_connection
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

    # Verify strict PostgreSQL connection
    db_ok = await verify_database_connection(max_retries=5, initial_delay=1.0)
    if not db_ok:
        logger.critical("Database connection validation failed! Shutting down.")
        raise RuntimeError("PostgreSQL database unavailable.")

    # Verify Redis connection
    redis_ok = await verify_redis_connection()
    if not redis_ok:
        logger.warning("Redis connection validation failed. Cache services compromised.")

    logger.info("Startup complete. System is healthy and accepting routes.")

    # Emit RECOVERY event on successful startup
    try:
        from app.core.event_bus import publish_event

        await publish_event("RECOVERY", "Newsroom core engine successfully restored.", "success")
    except Exception as e:
        logger.warning(f"Lifespan: Failed to emit RECOVERY event: {e}")

    yield  # Hand over execution to FastAPI

    # Notify active SSE connections to close gracefully
    from app.core.shutdown import shutdown_event

    shutdown_event.set()

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
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=response_content.model_dump(mode="json")
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    correlation_id = correlation_id_ctx.get() or "system"
    logger.error(f"Database transaction failure: {exc!s}", exc_info=True)
    error_details = ErrorDetails(
        code="DATABASE_ERROR", message="A secure database transaction encountered an operational exception."
    )
    response_content = ErrorResponse(correlation_id=correlation_id, error=error_details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response_content.model_dump(mode="json")
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    correlation_id = correlation_id_ctx.get() or "system"
    logger.error(f"Unhandled server exception: {exc!s}", exc_info=True)
    error_details = ErrorDetails(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please contact the technical administrator.",
    )
    response_content = ErrorResponse(correlation_id=correlation_id, error=error_details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response_content.model_dump(mode="json")
    )


# 2.5 Mount Security Headers Middleware
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# 3. Mount Security CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 4. Mount Production Logging & Correlation Middleware
app.add_middleware(MaintenanceModeMiddleware)
app.add_middleware(LoggingMiddleware)

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

# 7. Mount Versioned Router Tree
api_router.include_router(chat.router)
app.include_router(api_router, prefix=settings.API_V1_STR)
