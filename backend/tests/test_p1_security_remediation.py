from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.core.security import (
    clear_all_permission_caches,
    clear_permission_cache,
    is_allowed_cors_origin,
)
from main import app


def test_cors_origin_validator_allows_production_frontend():
    """Verify production frontend origin is recognized as allowed."""
    assert is_allowed_cors_origin("https://tech-news-alpha-eosin.vercel.app") is True


def test_cors_origin_validator_blocks_arbitrary_vercel_and_lookalike_origins():
    """Verify arbitrary .vercel.app domains and spoofed localhost names are rejected."""
    # Arbitrary vercel app
    assert is_allowed_cors_origin("https://attacker.vercel.app") is False
    assert is_allowed_cors_origin("https://evil-tech-news.vercel.app") is False
    # Spoofed localhost domains
    assert is_allowed_cors_origin("http://localhost.evil.com") is False
    assert is_allowed_cors_origin("http://attacker-localhost.com") is False
    assert is_allowed_cors_origin("http://127.0.0.1.attacker.com") is False
    # Empty or null origin
    assert is_allowed_cors_origin(None) is False
    assert is_allowed_cors_origin("") is False


def test_cors_in_production_rejects_localhost():
    """Verify localhost is rejected when running in production environment."""
    with patch.object(Settings, "effective_environment", new_callable=PropertyMock, return_value="production"):
        assert is_allowed_cors_origin("http://localhost:3000") is False
        assert is_allowed_cors_origin("http://127.0.0.1:3000") is False
        assert is_allowed_cors_origin("https://tech-news-alpha-eosin.vercel.app") is True


def test_cors_preflight_untrusted_origin_no_allow_headers():
    """Verify an untrusted Origin does not receive Access-Control-Allow-Origin header."""
    client = TestClient(app)
    response = client.options(
        "/api/v1/news",
        headers={
            "Origin": "https://evil-attacker.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "Access-Control-Allow-Origin" not in response.headers or response.headers["Access-Control-Allow-Origin"] != "https://evil-attacker.com"


def test_generic_exception_masks_trace_when_not_debug():
    """Verify unhandled exceptions return a generic message without internal traces when DEBUG=False."""
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/test-internal-error")
    def error_endpoint():
        raise RuntimeError("Sensitive internal database connection trace: secret_db_pw_123")

    with patch.object(settings, "DEBUG", False):
        res = client.get("/test-internal-error")
        assert res.status_code == 500
        data = res.json()
        assert "error" in data
        assert data["error"]["message"] == "An unexpected server error occurred."
        assert "secret_db_pw_123" not in res.text


def test_generic_exception_shows_trace_when_debug():
    """Verify unhandled exceptions include detail for local debugging when DEBUG=True."""
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/test-debug-internal-error")
    def error_debug_endpoint():
        raise RuntimeError("Debug detail: missing table xyz")

    with patch.object(settings, "DEBUG", True):
        res = client.get("/test-debug-internal-error")
        assert res.status_code == 500
        data = res.json()
        assert "Debug detail: missing table xyz" in data["error"]["message"]


@pytest.mark.asyncio
async def test_clear_permission_cache_redis_call():
    """Verify clear_permission_cache deletes the exact key from Redis."""
    mock_redis = AsyncMock()
    with patch("app.core.security.get_redis_client", return_value=mock_redis):
        await clear_permission_cache(42)
        mock_redis.delete.assert_called_once_with("user:permissions:42")


@pytest.mark.asyncio
async def test_clear_all_permission_caches_scan_and_delete():
    """Verify clear_all_permission_caches uses scan_iter and deletes matched keys."""
    mock_redis = AsyncMock()

    async def mock_scan_iter(match):
        for k in ["user:permissions:1", "user:permissions:2"]:
            yield k

    mock_redis.scan_iter = mock_scan_iter
    mock_redis.delete = AsyncMock(return_value=2)

    with patch("app.core.security.get_redis_client", return_value=mock_redis):
        cleared = await clear_all_permission_caches()
        assert cleared == 2
        mock_redis.delete.assert_called_once_with("user:permissions:1", "user:permissions:2")


def test_admin_permissions_cache_clear_requires_super_admin():
    """Verify /api/v1/admin/permissions/cache/clear requires super_admin authentication."""
    client = TestClient(app)
    res = client.post("/api/v1/admin/permissions/cache/clear")
    assert res.status_code == 401
