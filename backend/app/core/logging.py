import json
import logging
import os
import time

# Custom context storage for Correlation ID
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
        }
        # Add extra properties if available
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging(env: str = "development"):
    """
    Configures console formatters and rotating log files.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    # Avoid duplicate handlers
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO if env == "production" else logging.DEBUG)

    # 1. Console Handler (Plain colorized/readable for Dev, JSON for Prod)
    console_handler = logging.StreamHandler()
    if env == "production":
        console_handler.setFormatter(JSONFormatter())
    else:
        plain_format = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s")
        console_handler.setFormatter(plain_format)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler for production audits
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)


# FastAPI Middleware for correlation ID logging and timing
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        # Extract or generate X-Correlation-ID header
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        token = correlation_id_ctx.set(correlation_id)

        logger = logging.getLogger("tech_news.request")

        # Log request receipt
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={"extra_data": {"client_ip": request.client.host if request.client else "unknown"}},
        )

        try:
            response = await call_next(request)

            # Record request metrics
            process_time = (time.time() - start_time) * 1000
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

            origin = request.headers.get("origin")
            cors_headers = {k: v for k, v in response.headers.items() if k.lower().startswith("access-control-")}

            logger.info(
                f"Request completed: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Duration: {process_time:.2f}ms | "
                f"CORS Diagnostics: Origin: {origin} | CORS Headers: {cors_headers}"
            )
            return response

        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            origin = request.headers.get("origin")
            logger.error(
                f"Request failed: {request.method} {request.url.path} - "
                f"Exception: {e!s} - Duration: {process_time:.2f}ms | "
                f"CORS Diagnostics: Origin: {origin}",
                exc_info=True,
            )
            raise
        finally:
            correlation_id_ctx.reset(token)
