"""
OpenTelemetry Tracing — Auto-instrumentation + business operation spans.

Setup:
    - Auto-instrumentation for FastAPI, SQLAlchemy, Redis, Celery
    - Manual spans ONLY for meaningful business operations (not duplicating auto-instrumentation)
    - Console exporter by default (zero new infrastructure)
    - OTLP exporter available via OTEL_EXPORTER=otlp environment variable

CRITICAL: Never put prompts, article bodies, generated text, user content,
credentials, or PII into span attributes. Traces contain metadata only.
"""
import logging
import os

logger = logging.getLogger(__name__)


def init_tracing() -> None:
    """
    Initialize OpenTelemetry tracing with auto-instrumentation.

    Call this once during application startup (after DB/Redis verification).
    Gracefully degrades if opentelemetry packages are not installed.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )
    except ImportError:
        logger.info("OpenTelemetry SDK not installed — tracing disabled.")
        return

    resource = Resource.create({
        "service.name": "tech-news-backend",
        "service.version": os.getenv("APP_VERSION", "dev"),
        "deployment.environment": os.getenv("ENV", "development"),
    })

    provider = TracerProvider(resource=resource)

    exporter_type = os.getenv("OTEL_EXPORTER", "console").lower()
    if exporter_type == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            logger.info("OpenTelemetry: OTLP exporter configured.")
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp not installed, falling back to console."
            )
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        logger.info("OpenTelemetry: console exporter configured.")

    trace.set_tracer_provider(provider)

    # --- Auto-instrumentation (no manual spans needed for these) ---
    _instrument_fastapi()
    _instrument_sqlalchemy()
    _instrument_redis()
    _instrument_celery()

    logger.info("OpenTelemetry tracing initialized successfully.")


def _instrument_fastapi() -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor().instrument()
        logger.debug("FastAPI auto-instrumentation enabled.")
    except ImportError:
        logger.debug("FastAPI instrumentation package not available.")


def _instrument_sqlalchemy() -> None:
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        # Import the engine to instrument
        from app.core.database import async_engine
        if async_engine and hasattr(async_engine, "sync_engine"):
            SQLAlchemyInstrumentor().instrument(engine=async_engine.sync_engine)
            logger.debug("SQLAlchemy auto-instrumentation enabled.")
    except ImportError:
        logger.debug("SQLAlchemy instrumentation package not available.")
    except Exception as e:
        logger.warning(f"SQLAlchemy instrumentation failed: {e}")


def _instrument_redis() -> None:
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        logger.debug("Redis auto-instrumentation enabled.")
    except ImportError:
        logger.debug("Redis instrumentation package not available.")


def _instrument_celery() -> None:
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
        logger.debug("Celery auto-instrumentation enabled.")
    except ImportError:
        logger.debug("Celery instrumentation package not available.")


# ---------------------------------------------------------------------------
# Business Operation Tracer
# ---------------------------------------------------------------------------
# Use these for manual spans around meaningful business operations ONLY.
# Do NOT create manual spans for things auto-instrumentation already covers.
# ---------------------------------------------------------------------------

def get_tracer(name: str = "tech-news"):
    """Get a tracer instance for creating business-operation spans."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return None


# Attribute constants — safe metadata fields for spans.
# NEVER add: prompts, article bodies, generated text, user content, credentials, PII.
class SpanAttributes:
    """Approved span attribute keys for business operation spans."""

    # Article enrichment
    AI_PROVIDER = "ai.provider"
    AI_MODEL = "ai.model"
    AI_TOKENS = "ai.tokens"
    AI_COST_USD = "ai.cost_usd"
    AI_CACHE_HIT = "ai.cache_hit"

    # Knowledge extraction
    ARTICLE_ID = "article.id"
    ENTITIES_COUNT = "entities.count"
    RELATIONSHIPS_COUNT = "relationships.count"

    # Outbox dispatch
    BATCH_SIZE = "batch.size"
    BATCH_DELIVERED = "batch.delivered"
    BATCH_FAILED = "batch.failed"
    EVENT_TYPE = "event.type"
    EVENT_ID = "event.id"
    HANDLER_NAME = "handler.name"
