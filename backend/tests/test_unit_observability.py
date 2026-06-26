import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.monitoring import HealthSnapshot, HealthStatus, HistorySample
from app.services.monitoring.checkers import (
    BackendChecker,
    BeatChecker,
    PostgresChecker,
    RedisChecker,
    WorkerChecker,
)
from app.services.monitoring.observability import (
    calculate_health_grade,
)
from app.services.monitoring.repository import MonitoringRepository

# ---------------------------------------------------------------------------
# Health Score / Grade Tests
# ---------------------------------------------------------------------------


def test_health_grade_calculations():
    assert calculate_health_grade(100) == "A+"
    assert calculate_health_grade(98) == "A+"
    assert calculate_health_grade(97) == "A"
    assert calculate_health_grade(95) == "A"
    assert calculate_health_grade(94) == "B"
    assert calculate_health_grade(90) == "B"
    assert calculate_health_grade(89) == "C"
    assert calculate_health_grade(80) == "C"
    assert calculate_health_grade(79) == "F"
    assert calculate_health_grade(50) == "F"


# ---------------------------------------------------------------------------
# PostgresChecker Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_postgres_checker_online():
    checker = PostgresChecker()
    mock_db = AsyncMock()

    # Configure mock execute responses
    mock_db_size = MagicMock()
    mock_db_size.scalar.return_value = 52428800  # 50MB

    mock_cache = MagicMock()
    mock_cache.scalar.return_value = 0.985

    mock_longest = MagicMock()
    mock_longest.scalar.return_value = 0.42

    mock_db.execute.side_effect = [
        None,  # SELECT 1
        mock_db_size,  # db size query
        mock_cache,  # cache hit query
        mock_longest,  # longest query check
    ]

    with patch("app.services.monitoring.checkers.AsyncSessionLocal", return_value=mock_db):
        mock_db.__aenter__.return_value = mock_db
        res = await checker.check()

    assert res.service == "postgres"
    assert res.status == HealthStatus.ONLINE
    assert res.metrics["database_size_bytes"] == 52428800
    assert res.metrics["cache_hit_ratio"] == 0.985
    assert res.metrics["longest_running_query_sec"] == 0.42
    assert res.error is None


@pytest.mark.asyncio
async def test_postgres_checker_degraded_latency():
    checker = PostgresChecker()
    mock_db = AsyncMock()

    # Configure mock execute responses
    mock_db_size = MagicMock()
    mock_db_size.scalar.return_value = 52428800
    mock_cache = MagicMock()
    mock_cache.scalar.return_value = 0.985
    mock_longest = MagicMock()
    mock_longest.scalar.return_value = 0.42

    mock_db.execute.side_effect = [None, mock_db_size, mock_cache, mock_longest]

    # Inject delay using a sleep side effect on ping execution
    call_count = 0

    async def slow_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            await asyncio.sleep(0.15)  # 150ms > 100ms threshold
            return None
        elif call_count == 2:
            return mock_db_size
        elif call_count == 3:
            return mock_cache
        else:
            return mock_longest

    mock_db.execute.side_effect = slow_execute

    with patch("app.services.monitoring.checkers.AsyncSessionLocal", return_value=mock_db):
        mock_db.__aenter__.return_value = mock_db
        with patch.dict(
            "app.core.config.settings.HEALTH_THRESHOLDS",
            {"postgres": {"healthy": 10.0, "delayed": 50.0, "degraded": 100.0}},
        ):
            res = await checker.check()

    assert res.status == HealthStatus.DEGRADED
    assert "High latency" in res.error


@pytest.mark.asyncio
async def test_postgres_checker_offline_exception():
    checker = PostgresChecker()
    mock_db = AsyncMock()

    # Simulate DB connection error on context enter
    mock_db.__aenter__.side_effect = Exception("DB connection timeout")

    with patch("app.services.monitoring.checkers.AsyncSessionLocal", return_value=mock_db):
        res = await checker.check()

    assert res.status == HealthStatus.OFFLINE
    assert "DB connection timeout" in res.error


# ---------------------------------------------------------------------------
# RedisChecker Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_checker_online():
    checker = RedisChecker()
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.info.return_value = {
        "connected_clients": "5",
        "used_memory": "1048576",
        "uptime_in_seconds": "3600",
        "mem_fragmentation_ratio": "1.12",
        "db0": {"keys": 42},
    }

    with patch("app.services.monitoring.checkers.get_redis_client", return_value=mock_redis):
        res = await checker.check()

    assert res.service == "redis"
    assert res.status == HealthStatus.ONLINE
    assert res.metrics["uptime_seconds"] == 3600
    assert res.metrics["connected_clients"] == 5
    assert res.metrics["used_memory_bytes"] == 1048576
    assert res.metrics["key_count"] == 42
    assert res.metrics["fragmentation_ratio"] == 1.12
    assert res.error is None


@pytest.mark.asyncio
async def test_redis_checker_ping_failure():
    checker = RedisChecker()
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = False

    with patch("app.services.monitoring.checkers.get_redis_client", return_value=mock_redis):
        res = await checker.check()

    assert res.status == HealthStatus.OFFLINE
    assert "ping did not return true" in res.error.lower()


# ---------------------------------------------------------------------------
# WorkerChecker Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_checker_online():
    checker = WorkerChecker()

    mock_pings = {"worker1@tech-news": "pong", "worker2@tech-news": "pong"}
    mock_active = {"worker1@tech-news": [{}], "worker2@tech-news": []}

    # We need to mock celery_app and the control inspect ping/active methods
    mock_inspector = MagicMock()
    mock_inspector.ping.return_value = mock_pings
    mock_inspector.active.return_value = mock_active

    mock_celery = MagicMock()
    mock_celery.control.inspect.return_value = mock_inspector

    with patch.dict("sys.modules", {"celery_app": MagicMock(celery_app=mock_celery)}):
        res = await checker.check()

    assert res.service == "worker"
    assert res.status == HealthStatus.ONLINE
    assert res.metrics["workers_online"] == 2
    assert res.metrics["active_tasks"] == 1
    assert "worker1@tech-news" in res.metrics["workers"]


@pytest.mark.asyncio
async def test_worker_checker_no_workers():
    checker = WorkerChecker()

    mock_inspector = MagicMock()
    mock_inspector.ping.return_value = {}
    mock_inspector.active.return_value = {}

    mock_celery = MagicMock()
    mock_celery.control.inspect.return_value = mock_inspector

    with patch.dict("sys.modules", {"celery_app": MagicMock(celery_app=mock_celery)}):
        res = await checker.check()

    assert res.status == HealthStatus.OFFLINE
    assert "No active Celery workers" in res.error


# ---------------------------------------------------------------------------
# BeatChecker Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_beat_checker_online():
    checker = BeatChecker()
    mock_redis = AsyncMock()

    # Simulate a very recent heartbeat (5 seconds ago)
    recent_ts = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    mock_redis.get.return_value = recent_ts.encode("utf-8")

    with patch("app.services.monitoring.checkers.get_redis_client", return_value=mock_redis):
        res = await checker.check()

    assert res.service == "beat"
    assert res.status == HealthStatus.ONLINE
    assert res.metrics["heartbeat_age_seconds"] == 5.0
    assert res.error is None


# ---------------------------------------------------------------------------
# Backend & Nginx HTTP Checkers Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backend_checker_online():
    checker = BackendChecker()
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        res = await checker.check()

    assert res.service == "backend"
    assert res.status == HealthStatus.ONLINE
    assert res.metrics["status_code"] == 200
    assert res.error is None


# ---------------------------------------------------------------------------
# MonitoringRepository Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repo_get_health_snapshot_success():
    repo = MonitoringRepository()
    mock_redis = AsyncMock()

    now_str = datetime.now(timezone.utc).isoformat()
    snap = HealthSnapshot(
        service="postgres", status=HealthStatus.ONLINE, latency_ms=5.0, last_checked=now_str, metrics={}
    )

    mock_redis.get.return_value = snap.model_dump_json().encode("utf-8")

    with patch("app.services.monitoring.repository.get_redis_client", return_value=mock_redis):
        res = await repo.get_health_snapshot("postgres")

    assert res is not None
    assert res.service == "postgres"
    assert res.status == HealthStatus.ONLINE
    assert res.latency_ms == 5.0


@pytest.mark.asyncio
async def test_repo_get_health_snapshot_stale():
    repo = MonitoringRepository()
    mock_redis = AsyncMock()

    # 30 seconds ago (expected interval for postgres is 10s, stale age boundary is 2 * 10 = 20s)
    stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=25)).isoformat()
    snap = HealthSnapshot(
        service="postgres", status=HealthStatus.ONLINE, latency_ms=5.0, last_checked=stale_ts, metrics={}
    )

    mock_redis.get.return_value = snap.model_dump_json().encode("utf-8")

    with patch("app.services.monitoring.repository.get_redis_client", return_value=mock_redis):
        res = await repo.get_health_snapshot("postgres")

    assert res is not None
    assert res.status == HealthStatus.UNKNOWN
    assert "Cache stale" in res.error


@pytest.mark.asyncio
async def test_repo_get_history():
    repo = MonitoringRepository()
    mock_redis = AsyncMock()

    ts1 = datetime.now(timezone.utc).isoformat()
    sample = HistorySample(timestamp=ts1, status=HealthStatus.ONLINE, latency_ms=4.2)

    mock_redis.lrange.return_value = [sample.model_dump_json().encode("utf-8")]

    with patch("app.services.monitoring.repository.get_redis_client", return_value=mock_redis):
        history = await repo.get_history("postgres")

    assert len(history) == 1
    assert history[0].status == HealthStatus.ONLINE
    assert history[0].latency_ms == 4.2


@pytest.mark.asyncio
async def test_repo_get_overview_freshness():
    repo = MonitoringRepository()
    mock_redis = AsyncMock()

    # Generated 150 seconds ago (exceeds 120s limit)
    stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=150)).isoformat()
    overview_data = {
        "generated_at": stale_ts,
        "source_health": {"total": 10, "healthy": 9, "degraded": 1, "failed": 0},
        "article_pipeline": {"raw": 100, "processed": 80, "published": 50, "draft": 30, "rejected": 20},
        "ai_queue": {"queued": 0, "processing": 0, "completed": 100, "failed": 0, "retry": 0},
        "emergency_cutoff_active": False,
    }

    mock_redis.get.return_value = json.dumps(overview_data).encode("utf-8")

    with patch("app.services.monitoring.repository.get_redis_client", return_value=mock_redis):
        res = await repo.get_overview()

    assert res is not None
    assert res.get("stale") is True
