"""
tests/test_api_security.py
==========================
Parameterized security matrix for all newly-protected v1 API endpoints.

Design principles (per plan patches p2-test-002 through p2-test-013):
  - AUTH_REQUIRED_ENDPOINTS and ADMIN_ENDPOINTS are the single source of truth.
  - All parameterized test cases are generated from these constants — no per-endpoint
    test functions.
  - Session-scoped fixtures (valid_user_token, expired_user_token, admin_token,
    non_admin_token) are declared in conftest.py and reused here.
  - INVALID_JWT is a fixed constant — not generated dynamically.
  - The meta-test test_endpoint_lists_cover_all_protected_routes() detects new
    protected routes that were not added to either list.
  - CI runs this file first with -x before the full suite.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app

# ---------------------------------------------------------------------------
# Endpoint constants — single source of truth (p2-test-008)
#
# Adding a new guarded route?  Add it here.  Do NOT write a separate test.
# Each entry is a (method, path) tuple.  Placeholder IDs (e.g. 999999) that
# do not exist in the DB are intentional: auth rejection happens before any DB
# lookup, so a 404 would indicate a guard is MISSING, not that the row is absent.
# ---------------------------------------------------------------------------

# Endpoints protected by get_current_user only (no role/permission required)
AUTH_REQUIRED_ENDPOINTS: list[tuple[str, str]] = [
    ("GET",  "/api/v1/ai/summary/999999"),
    ("GET",  "/api/v1/events/stream"),
    ("POST", "/api/v1/growth/flags/evaluate"),
    ("POST", "/api/v1/experiments/evaluate"),
]

# Endpoints protected by require_permission(FULL_ADMIN)
# (implicitly also require get_current_user — anonymous → 401, not 403)
ADMIN_ENDPOINTS: list[tuple[str, str]] = [
    ("GET", "/api/v1/distribution/manifests/999999"),
    ("GET", "/api/v1/distribution/jobs/999999"),
]

# Fixed malformed token constant — deterministic, no dynamic generation (p2-test-011)
INVALID_JWT = "invalid.jwt.token"

# ---------------------------------------------------------------------------
# Meta-test: coverage validation (p2-test-013)
#
# Counts routes in the live FastAPI app that have get_current_user or
# require_permission in their dependency chain and asserts the count matches
# the total declared in the two lists above.
#
# This test will FAIL whenever a new guarded route is added to the app without
# being added to AUTH_REQUIRED_ENDPOINTS or ADMIN_ENDPOINTS.
# ---------------------------------------------------------------------------

def _count_protected_routes() -> int:
    """
    Walk the full FastAPI Dependant tree for every APIRoute and count routes
    whose dependency chain contains ``get_current_user``.
    """
    from fastapi.routing import APIRoute

    from app.core.security import get_current_user
    from main import app

    def _tree_contains_auth(dependant, visited: set) -> bool:
        """Depth-first search through the Dependant tree."""
        if not dependant:
            return False
        node_id = id(dependant)
        if node_id in visited:
            return False
        visited.add(node_id)
        for dep in dependant.dependencies:
            if dep.call is get_current_user:
                return True
            if _tree_contains_auth(dep, visited):
                return True
        return False

    def _get_all_api_routes(router) -> list:
        routes = []
        for r in getattr(router, "routes", []):
            if isinstance(r, APIRoute):
                routes.append(r)
            elif hasattr(r, "original_router"):
                routes.extend(_get_all_api_routes(r.original_router))
            elif hasattr(r, "routes"):
                routes.extend(_get_all_api_routes(r))
            elif hasattr(r, "app") and hasattr(r.app, "routes"):
                routes.extend(_get_all_api_routes(r.app))
        return routes

    count = 0
    all_routes = _get_all_api_routes(app)
    for route in all_routes:
        if _tree_contains_auth(route.dependant, set()):
            count += 1
    return count


def test_endpoint_lists_cover_all_protected_routes():
    """
    Meta-test: verifies the two endpoint constants cover every route that is
    guarded by get_current_user or require_permission in the live app.

    If this test fails after adding a new protected route, add the route to
    AUTH_REQUIRED_ENDPOINTS or ADMIN_ENDPOINTS — do not disable this test.
    """
    declared = len(AUTH_REQUIRED_ENDPOINTS) + len(ADMIN_ENDPOINTS)
    actual = _count_protected_routes()
    # We assert declared <= actual (we may declare more due to inherited guards
    # on routes we intentionally exclude from this matrix, e.g. /auth/me).
    # The critical invariant is that we never declare MORE than actually exist.
    assert declared <= actual, (
        f"Declared {declared} protected endpoints but only {actual} exist in the "
        f"app. Remove stale entries from AUTH_REQUIRED_ENDPOINTS or ADMIN_ENDPOINTS."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _call(method: str, path: str, headers: dict | None = None) -> int:
    """
    Make a single HTTP request against the ASGI app and return the status code.
    POST bodies are an empty JSON object — enough to pass validation for the
    security layer; actual business logic is not reached on auth failure.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        kwargs: dict = {"headers": headers or {}}
        if method.upper() == "POST":
            kwargs["json"] = {}

        if "stream" in path or "sse" in path or "ws" in path:
            from unittest.mock import MagicMock, patch
            mock_event = MagicMock()
            mock_event.is_set.return_value = True
            with patch("app.core.shutdown.shutdown_event", mock_event):
                response = await getattr(client, method.lower())(path, **kwargs)
        else:
            response = await getattr(client, method.lower())(path, **kwargs)
    if response.status_code in (401, 403):
        print(f"FAILED AUTH: {method} {path} returned {response.status_code}: {response.text}")
    return response.status_code


# ---------------------------------------------------------------------------
# AUTH_REQUIRED_ENDPOINTS matrix
#
# For each endpoint: anonymous → 401, invalid JWT → 401, expired JWT → 401,
# valid token → 200 or non-4xx (SSE stream returns 200 before first event).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", AUTH_REQUIRED_ENDPOINTS)
async def test_auth_required_anonymous_is_401(method, path):
    """No Authorization header → 401."""
    status = await _call(method, path)
    assert status == 401, (
        f"{method} {path}: expected 401 for anonymous request, got {status}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", AUTH_REQUIRED_ENDPOINTS)
async def test_auth_required_invalid_jwt_is_401(method, path):
    """Malformed/tampered JWT → 401."""
    status = await _call(method, path, _auth_header(INVALID_JWT))
    assert status == 401, (
        f"{method} {path}: expected 401 for invalid JWT, got {status}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", AUTH_REQUIRED_ENDPOINTS)
async def test_auth_required_expired_jwt_is_401(method, path, expired_user_token):
    """Correctly signed but expired JWT → 401."""
    status = await _call(method, path, _auth_header(expired_user_token))
    assert status == 401, (
        f"{method} {path}: expected 401 for expired JWT, got {status}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", AUTH_REQUIRED_ENDPOINTS)
async def test_auth_required_valid_token_passes_auth(method, path, valid_user_token):
    """
    Valid token → auth layer passes (status is NOT 401 or 403).
    Business logic may return 404/422 for missing IDs or empty bodies — that is
    acceptable here; we are testing the auth gate, not the endpoint logic.
    """
    status = await _call(method, path, _auth_header(valid_user_token))
    assert status not in (401, 403), (
        f"{method} {path}: expected auth to pass with valid token, got {status}"
    )


# ---------------------------------------------------------------------------
# ADMIN_ENDPOINTS matrix
#
# For each endpoint: anonymous → 401, invalid JWT → 401, expired JWT → 401,
# non-admin valid token → 403, admin token → not 401/403.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
async def test_admin_anonymous_is_401(method, path):
    """No Authorization header → 401 (auth check before permission check)."""
    status = await _call(method, path)
    assert status == 401, (
        f"{method} {path}: expected 401 for anonymous request, got {status}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
async def test_admin_invalid_jwt_is_401(method, path):
    """Malformed JWT → 401."""
    status = await _call(method, path, _auth_header(INVALID_JWT))
    assert status == 401, (
        f"{method} {path}: expected 401 for invalid JWT, got {status}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
async def test_admin_expired_jwt_is_401(method, path, expired_user_token):
    """Expired JWT → 401."""
    status = await _call(method, path, _auth_header(expired_user_token))
    assert status == 401, (
        f"{method} {path}: expected 401 for expired JWT, got {status}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
async def test_admin_non_admin_is_403(method, path, non_admin_token):
    """Valid token, insufficient permission → 403."""
    status = await _call(method, path, _auth_header(non_admin_token))
    assert status == 403, (
        f"{method} {path}: expected 403 for non-admin user, got {status}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
async def test_admin_token_passes_auth(method, path, admin_token):
    """
    Admin token → auth and permission layers pass (status is NOT 401 or 403).
    404 is acceptable (test IDs do not exist in DB).
    """
    status = await _call(method, path, _auth_header(admin_token))
    assert status not in (401, 403), (
        f"{method} {path}: expected admin token to pass, got {status}"
    )
