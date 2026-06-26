from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.core.security import (
    apply_rate_limit,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_current_user,
    hash_password,
    require_permission,
    require_role,
    verify_password,
)
from app.models.user import Role, User
from main import SecurityHeadersMiddleware

# ---------------------------------------------------------------------------
# Password Hashing Tests
# ---------------------------------------------------------------------------


def test_password_hashing():
    plain = "SuperSecurePassword123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert verify_password(plain, "invalid_hash_string") is False


# ---------------------------------------------------------------------------
# JWT Token Tests
# ---------------------------------------------------------------------------


def test_jwt_token_operations():
    data = {"sub": "42", "role": "editor", "permissions": ["edit_articles"]}
    token = create_access_token(data)
    assert isinstance(token, str)

    # Decode and verify payload
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "editor"
    assert "exp" in payload

    # Test expired token
    with patch("app.core.config.settings.ACCESS_TOKEN_EXPIRE_MINUTES", -5):
        expired_token = create_access_token(data)
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(expired_token)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in exc_info.value.detail.lower()

    # Test invalid signature/token
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("this.isnot.avalidtoken")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "invalid" in exc_info.value.detail.lower()

    # Create refresh token
    ref_token = create_refresh_token()
    assert len(ref_token) == 128  # secrets.token_hex(64) has length 128 hex chars


# ---------------------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_rate_limit_success():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock()
    mock_redis.get.return_value = None

    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock()
    mock_redis.pipeline.return_value = mock_pipe

    mock_request = MagicMock()
    mock_request.client.host = "12.34.56.78"

    with patch("app.core.security.get_redis_client", return_value=mock_redis):
        # Should execute successfully without throwing an exception
        await apply_rate_limit(mock_request, "login", max_requests=3, window_seconds=30)

    mock_redis.get.assert_called_once_with("rate_limit:login:12.34.56.78")
    mock_redis.pipeline.assert_called_once()
    mock_pipe.incr.assert_called_once_with("rate_limit:login:12.34.56.78")
    mock_pipe.expire.assert_called_once_with("rate_limit:login:12.34.56.78", 30)
    mock_pipe.execute.assert_called_once()


@pytest.mark.asyncio
async def test_apply_rate_limit_exceeded():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock()
    mock_redis.get.return_value = "3"

    mock_request = MagicMock()
    mock_request.client.host = "12.34.56.78"

    with patch("app.core.security.get_redis_client", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await apply_rate_limit(mock_request, "login", max_requests=3, window_seconds=30)
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "too many attempts" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# FastAPI Dependency Tests (Current User, Role & Permissions Checks)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_success():
    role = Role(name="editor")
    user = User(id=12, email="editor@example.com", status="active", role=role)
    token_data = {"sub": "12", "role": "editor"}
    token = create_access_token(token_data)

    mock_request = MagicMock()
    mock_request.headers = {"Authorization": f"Bearer {token}"}

    # Mock DB Session response
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    res_user = await get_current_user(mock_request, db=mock_db)
    assert res_user == user
    assert res_user.id == 12
    assert res_user.role.name == "editor"


@pytest.mark.asyncio
async def test_get_current_user_inactive():
    role = Role(name="editor")
    user = User(id=12, email="editor@example.com", status="suspended", role=role)
    token_data = {"sub": "12", "role": "editor"}
    token = create_access_token(token_data)

    mock_request = MagicMock()
    mock_request.headers = {"Authorization": f"Bearer {token}"}

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_request, db=mock_db)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "suspended" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_missing_auth():
    mock_request = MagicMock()
    mock_request.headers = {}

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_request)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "missing or invalid" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_role_success():
    role = Role(name="admin")
    user = User(id=1, email="admin@example.com", status="active", role=role)

    checker = require_role("admin", "editor")
    res = await checker(current_user=user)
    assert res == user


@pytest.mark.asyncio
async def test_require_role_insufficient():
    role = Role(name="user")
    user = User(id=5, email="user@example.com", status="active", role=role)

    checker = require_role("admin", "editor")
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "insufficient role" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_permission_cached_success():
    role = Role(name="editor")
    user = User(id=5, email="editor@example.com", status="active", role_id=2, role=role)

    checker = require_permission("publish_articles")
    mock_request = MagicMock()
    mock_db = AsyncMock()

    with patch("app.core.security.get_cached_permissions", return_value=["publish_articles", "edit_articles"]):
        res = await checker(mock_request, current_user=user, db=mock_db)
        assert res == user
        mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_require_permission_db_fallback_success():
    role = Role(name="editor")
    user = User(id=5, email="editor@example.com", status="active", role_id=2, role=role)

    checker = require_permission("publish_articles")
    mock_request = MagicMock()
    mock_db = AsyncMock()

    # Mock permission query result
    mock_result = MagicMock()
    mock_result.all.return_value = [("publish_articles",), ("edit_articles",)]
    mock_db.execute.return_value = mock_result

    with patch("app.core.security.get_cached_permissions", return_value=None):
        with patch("app.core.security.cache_user_permissions") as mock_cache:
            res = await checker(mock_request, current_user=user, db=mock_db)
            assert res == user
            mock_cache.assert_called_once_with(5, ["publish_articles", "edit_articles"])


@pytest.mark.asyncio
async def test_require_permission_missing():
    role = Role(name="user")
    user = User(id=5, email="user@example.com", status="active", role_id=1, role=role)

    checker = require_permission("delete_users")
    mock_request = MagicMock()
    mock_db = AsyncMock()

    with patch("app.core.security.get_cached_permissions", return_value=["read_articles"]):
        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_request, current_user=user, db=mock_db)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "missing required permission" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Security Headers Middleware Tests
# ---------------------------------------------------------------------------


def test_security_headers_middleware():
    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware)

    @test_app.get("/test-endpoint")
    def dummy_route():
        return {"ok": True}

    client = TestClient(test_app)
    response = client.get("/test-endpoint")

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    # Test strict transport security header in production
    with patch("app.core.config.settings.ENV", "production"):
        response_prod = client.get("/test-endpoint")
        assert response_prod.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
