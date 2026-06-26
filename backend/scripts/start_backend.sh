#!/bin/bash
set -e

echo "PostgreSQL should be ready (via depends_on)."

echo "Running migrations..."
alembic upgrade head

echo "Running initial database seeding..."
python -m app.core.init_db

echo "Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
