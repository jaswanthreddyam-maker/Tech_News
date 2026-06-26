from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import MaintenanceModeMiddleware


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(MaintenanceModeMiddleware)

    @app.get("/api/v1/health/live")
    async def live():
        return {"ok": True}

    @app.get("/api/v1/telemetry/sse")
    async def telemetry_sse():
        return {"ok": True}

    @app.post("/api/v1/auth/login")
    async def login():
        return {"ok": True}

    @app.post("/api/v1/backup/restore")
    async def restore():
        return {"ok": True}

    @app.post("/api/v1/backup-extra")
    async def backup_extra():
        return {"ok": True}

    return app


def test_maintenance_allows_read_only_operational_routes():
    redis = AsyncMock()
    redis.get.return_value = "1"

    with patch("app.core.middleware.get_redis_client", return_value=redis):
        with TestClient(build_test_app()) as client:
            assert client.get("/api/v1/health/live").status_code == 200
            assert client.get("/api/v1/telemetry/sse").status_code == 200

    redis.get.assert_not_called()


def test_maintenance_blocks_state_changing_requests():
    redis = AsyncMock()
    redis.get.return_value = "1"

    with patch("app.core.middleware.get_redis_client", return_value=redis):
        with TestClient(build_test_app()) as client:
            response = client.post("/api/v1/auth/login")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MAINTENANCE_MODE"
    redis.get.assert_awaited_once_with("settings:maintenance_mode")


def test_maintenance_allows_backup_restore_requests():
    redis = AsyncMock()
    redis.get.return_value = "1"

    with patch("app.core.middleware.get_redis_client", return_value=redis):
        with TestClient(build_test_app()) as client:
            response = client.post("/api/v1/backup/restore")

    assert response.status_code == 200
    redis.get.assert_awaited_once_with("settings:maintenance_mode")


def test_maintenance_bypass_does_not_overmatch_similar_paths():
    redis = AsyncMock()
    redis.get.return_value = "1"

    with patch("app.core.middleware.get_redis_client", return_value=redis):
        with TestClient(build_test_app()) as client:
            response = client.post("/api/v1/backup-extra")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MAINTENANCE_MODE"
