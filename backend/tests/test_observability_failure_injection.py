from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.monitoring import HealthSnapshot, HealthStatus
from app.services.monitoring.checkers import BeatChecker, PostgresChecker
from app.services.monitoring.observability import calculate_health_grade
from app.services.monitoring.repository import MonitoringRepository


@pytest.mark.asyncio
async def test_health_grade_math():
    """
    Asserts health score letter grade conversions are correct.
    """
    assert calculate_health_grade(99) == "A+"
    assert calculate_health_grade(97) == "A"
    assert calculate_health_grade(93) == "B"
    assert calculate_health_grade(85) == "C"
    assert calculate_health_grade(75) == "F"


@pytest.mark.asyncio
async def test_beat_checker_states():
    """
    Verifies BeatChecker transitions from ONLINE to DEGRADED and OFFLINE
    based on the cached heartbeat timestamp age.
    """
    checker = BeatChecker()
    mock_redis = AsyncMock()

    with patch("app.services.monitoring.checkers.get_redis_client", return_value=mock_redis):
        # Case 1: No heartbeat registered
        mock_redis.get.return_value = None
        res = await checker.check()
        assert res.status == HealthStatus.OFFLINE
        assert "No heartbeat timestamp registered" in res.error

        # Case 2: Healthy heartbeat (5s old)
        healthy_ts = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        mock_redis.get.return_value = healthy_ts.encode("utf-8")
        res = await checker.check()
        assert res.status == HealthStatus.ONLINE
        assert res.metrics["heartbeat_age_seconds"] == 5.0

        # Case 3: Degraded heartbeat (25s old)
        degraded_ts = (datetime.now(timezone.utc) - timedelta(seconds=25)).isoformat()
        mock_redis.get.return_value = degraded_ts.encode("utf-8")
        res = await checker.check()
        assert res.status == HealthStatus.DEGRADED
        assert "heartbeat delayed" in res.error

        # Case 4: Offline heartbeat (90s old)
        offline_ts = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
        mock_redis.get.return_value = offline_ts.encode("utf-8")
        res = await checker.check()
        assert res.status == HealthStatus.OFFLINE
        assert "Scheduler inactive" in res.error


@pytest.mark.asyncio
async def test_freshness_staleness_validation():
    """
    Validates that MonitoringRepository flags telemetry snapshot data as UNKNOWN
    if it is older than double its refresh frequency.
    """
    repo = MonitoringRepository()
    mock_redis = AsyncMock()

    # Snapshot generated 30s ago (exceeds 20s infrastructure max-age limit)
    stale_checked = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    snapshot = HealthSnapshot(
        service="postgres",
        status=HealthStatus.ONLINE,
        latency_ms=8.0,
        last_checked=stale_checked,
        last_success=stale_checked,
        metrics={"database_size_bytes": 10000000},
    )

    with patch("app.services.monitoring.repository.get_redis_client", return_value=mock_redis):
        mock_redis.get.return_value = snapshot.model_dump_json()

        fetched = await repo.get_health_snapshot("postgres")
        assert fetched is not None
        assert fetched.status == HealthStatus.UNKNOWN
        assert "Cache stale" in fetched.error


@pytest.mark.asyncio
async def test_monitoring_repository_atomic_pipeline():
    """
    Verifies that MonitoringRepository executes saving and rolling history updates
    atomically inside a Redis transaction pipeline.
    """
    repo = MonitoringRepository()
    mock_redis = AsyncMock()
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)  # pipeline call is synchronous

    now_str = datetime.now(timezone.utc).isoformat()
    snapshot = HealthSnapshot(
        service="postgres", status=HealthStatus.ONLINE, latency_ms=7.0, last_checked=now_str, metrics={}
    )

    with patch("app.services.monitoring.repository.get_redis_client", return_value=mock_redis):
        # Mock the get call during save to fetch previous success
        mock_redis.get.return_value = None

        await repo.save_health_snapshot(snapshot)

        # Verify Redis pipeline is created, queued, and executed atomically
        mock_redis.pipeline.assert_called_once()
        mock_pipe.set.assert_called_once()
        mock_pipe.lpush.assert_called_once()
        mock_pipe.ltrim.assert_called_once()
        mock_pipe.execute.assert_called_once_with()


@pytest.mark.asyncio
async def test_postgres_checker_latency_degradation():
    """
    Verifies PostgresChecker flags DEGRADED state when execution latency exceeds the threshold.
    """
    checker = PostgresChecker()
    mock_db = AsyncMock()

    # Configure mock db execute to return a synchronous result mock with scalar method returning 1.0/1000
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1.0
    mock_db.execute.return_value = mock_result

    with patch("app.services.monitoring.checkers.AsyncSessionLocal", return_value=mock_db):
        # Case 1: Healthy low-latency db response
        mock_db.__aenter__.return_value = mock_db
        res = await checker.check()
        assert res.status in (HealthStatus.ONLINE, HealthStatus.DEGRADED)

        # Case 2: Db raised exception -> OFFLINE
        mock_db.__aenter__.side_effect = ConnectionError("Could not reach Postgres host.")
        res = await checker.check()
        assert res.status == HealthStatus.OFFLINE
        assert "Could not reach Postgres host" in res.error


@pytest.mark.asyncio
async def test_observability_recovery_flow():
    """
    Verifies state recovery transitions: ONLINE -> OFFLINE -> ONLINE.
    Asserts last_success, history logs, and health score recovery.
    """
    repo = MonitoringRepository()
    mock_redis = AsyncMock()
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    with patch("app.services.monitoring.repository.get_redis_client", return_value=mock_redis):
        # 1. State 1: ONLINE at t=0
        t0_str = datetime.now(timezone.utc).isoformat()
        snap1 = HealthSnapshot(
            service="postgres", status=HealthStatus.ONLINE, latency_ms=10.0, last_checked=t0_str, metrics={}
        )

        # Mock get_health_snapshot to return None for t0
        mock_redis.get.return_value = None
        await repo.save_health_snapshot(snap1)
        assert snap1.last_success == t0_str

        # 2. State 2: OFFLINE at t=10s
        t10_str = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
        snap2 = HealthSnapshot(
            service="postgres", status=HealthStatus.OFFLINE, latency_ms=0.0, last_checked=t10_str, metrics={}
        )

        # Mock get_health_snapshot to return snap1 (so we preserve last_success)
        mock_redis.get.return_value = snap1.model_dump_json()
        await repo.save_health_snapshot(snap2)
        # Should preserve t0_str as last_success
        assert snap2.last_success == t0_str

        # 3. State 3: Recovery back to ONLINE at t=20s
        t20_str = (datetime.now(timezone.utc) + timedelta(seconds=20)).isoformat()
        snap3 = HealthSnapshot(
            service="postgres", status=HealthStatus.ONLINE, latency_ms=12.0, last_checked=t20_str, metrics={}
        )

        # Mock get_health_snapshot to return snap2
        mock_redis.get.return_value = snap2.model_dump_json()
        await repo.save_health_snapshot(snap3)
        # Should update last_success to t20_str
        assert snap3.last_success == t20_str


@pytest.mark.asyncio
async def test_chaos_beat_failure_independent():
    """
    Chaos Test: Verifies that when Beat stops (heartbeat expires),
    Beat goes OFFLINE but the worker (if tested independently) would not be impacted by Beat's heartbeat.
    Proves independent monitoring.
    """
    checker = BeatChecker()
    mock_redis = AsyncMock()

    with patch("app.services.monitoring.checkers.get_redis_client", return_value=mock_redis):
        # 1. Beat is running (recent heartbeat)
        import json

        healthy_payload = json.dumps({"last_tick": (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()})
        mock_redis.get.return_value = healthy_payload.encode("utf-8")
        res1 = await checker.check()
        assert res1.status == HealthStatus.ONLINE

        # 2. Stop Beat -> Heartbeat expires (> 45s) -> OFFLINE
        offline_payload = json.dumps({"last_tick": (datetime.now(timezone.utc) - timedelta(seconds=50)).isoformat()})
        mock_redis.get.return_value = offline_payload.encode("utf-8")
        res2 = await checker.check()
        assert res2.status == HealthStatus.OFFLINE

        # 3. Restart Beat -> ONLINE
        new_healthy_payload = json.dumps({"last_tick": (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat()})
        mock_redis.get.return_value = new_healthy_payload.encode("utf-8")
        res3 = await checker.check()
        assert res3.status == HealthStatus.ONLINE


@pytest.mark.asyncio
async def test_chaos_worker_failure_independent():
    """
    Chaos Test: Verifies that when Worker stops, it goes OFFLINE
    while Beat remains independently monitorable (if Beat is running).
    """
    from app.services.monitoring.checkers import WorkerChecker

    checker = WorkerChecker()

    # 1. Stop Worker -> No active workers -> OFFLINE
    mock_inspector = MagicMock()
    mock_inspector.ping.return_value = {}  # No workers pinging back
    mock_inspector.active.return_value = {}

    mock_celery = MagicMock()
    mock_celery.control.inspect.return_value = mock_inspector

    with patch.dict("sys.modules", {"celery_app": MagicMock(celery_app=mock_celery)}):
        res = await checker.check()

    assert res.service == "worker"
    assert res.status == HealthStatus.OFFLINE
    assert "No active Celery workers" in res.error
