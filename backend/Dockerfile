# Production Multi-Stage Dockerfile for FastAPI / Celery Worker / Celery Beat on Railway
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime system libraries (libpq for postgresql asyncpg/psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed site-packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY . /app

# Set environment defaults
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000

# Expose default HTTP port
EXPOSE 8000

# Default command for Railway FastAPI service (overridden by worker/beat service start commands)
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
