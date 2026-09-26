import os
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.services.ingestion.image_helper import _request_with_ssrf_protection, is_safe_url
from main import app


def test_production_fails_with_default_jwt_secret():
    """Verify that Settings raises RuntimeError when JWT_SECRET_KEY is default in production."""
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "SECRET_KEY": "a_valid_custom_production_secret_key_32_chars_minimum",
            "JWT_SECRET_KEY": "phase4_dev_jwt_secret_key_change_in_production_64chars_minimum_okay",
            "BACKUP_ENCRYPTION_KEY": "custom_prod_backup_encryption_key_32bytes",
            "BACKUP_SIGNING_KEY": "custom_prod_backup_signing_key_32bytes!",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/tech_news_today",
            "REDIS_URL": "redis://localhost:6379/0",
            "BACKEND_CORS_ORIGINS": '["https://example.com"]',
        },
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be explicitly configured in production"):
            Settings()


def test_production_fails_with_default_secret_key():
    """Verify that Settings raises RuntimeError when SECRET_KEY is default in production."""
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "SECRET_KEY": "supersecretkey_change_me_in_production_32_chars_long",
            "JWT_SECRET_KEY": "custom_prod_jwt_secret_key_64_characters_long_for_security_testing!",
            "BACKUP_ENCRYPTION_KEY": "custom_prod_backup_encryption_key_32bytes",
            "BACKUP_SIGNING_KEY": "custom_prod_backup_signing_key_32bytes!",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/tech_news_today",
            "REDIS_URL": "redis://localhost:6379/0",
            "BACKEND_CORS_ORIGINS": '["https://example.com"]',
        },
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="SECRET_KEY must be explicitly configured in production"):
            Settings()


def test_is_safe_url_rejects_embedded_credentials():
    """Verify is_safe_url blocks URLs with embedded credentials."""
    assert is_safe_url("https://user:password@example.com/image.jpg") is False
    assert is_safe_url("http://admin:@example.com/image.png") is False


def test_is_safe_url_rejects_private_and_loopback_ips():
    """Verify is_safe_url blocks loopback, private RFC1918, and link-local ranges."""
    assert is_safe_url("http://127.0.0.1/test.png") is False
    assert is_safe_url("http://localhost/test.png") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_url("http://10.0.0.1/image.jpg") is False
    assert is_safe_url("http://192.168.1.1/image.jpg") is False


@pytest.mark.asyncio
async def test_ssrf_protection_blocks_redirect_to_private_ip():
    """Verify _request_with_ssrf_protection blocks redirects to private/internal IPs."""
    mock_client = AsyncMock()

    # First response is a 302 redirecting to AWS metadata
    first_resp = AsyncMock()
    first_resp.status_code = 302
    first_resp.headers = {"location": "http://169.254.169.254/latest/meta-data/"}

    mock_client.get.return_value = first_resp

    with patch("app.services.ingestion.image_helper.is_safe_url") as mock_safe:
        # First URL safe, redirect target blocked
        mock_safe.side_effect = lambda u: "169.254" not in u

        resp = await _request_with_ssrf_protection(
            client=mock_client,
            method="GET",
            url="https://example.com/redirect-to-metadata",
        )
        assert resp is None


def test_admin_diagnostics_require_authentication():
    """Verify /api/v1/admin/diagnostic/db-truth and filtered-samples require super_admin."""
    client = TestClient(app)

    res_truth = client.get("/api/v1/admin/diagnostic/db-truth")
    assert res_truth.status_code == 401

    res_samples = client.get("/api/v1/admin/diagnostic/filtered-samples")
    assert res_samples.status_code == 401


def test_redis_diag_requires_authentication():
    """Verify /health/redis-diag requires super_admin authentication."""
    client = TestClient(app)

    res = client.get("/health/redis-diag")
    assert res.status_code == 401


def test_redis_diag_disabled_in_production():
    """Verify /health/redis-diag returns 404 in production."""
    with patch.object(Settings, "effective_environment", new_callable=PropertyMock, return_value="production"):
        from app.core.security import get_current_user
        from app.models.user import Role, User

        super_admin_user = User(id=1, email="admin@test.com", status="active")
        super_admin_user.role = Role(id=1, name="super_admin")

        app.dependency_overrides[get_current_user] = lambda: super_admin_user
        try:
            client = TestClient(app)
            res = client.get("/health/redis-diag")
            assert res.status_code == 404
        finally:
            app.dependency_overrides.clear()
