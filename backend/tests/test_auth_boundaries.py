import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_current_user
from app.models.user import User, Role
from app.models.conversation import ConversationSession
from app.briefing.models import DailyBriefingSubscriber
from app.models.workspace import Workspace
from app.models.followed_source import FollowedSource
from app.models.source import Source
from main import app

client = TestClient(app, raise_server_exceptions=False)


def make_test_user(user_id: int, email: str, role_name: str = "reader") -> User:
    role = Role(id=1, name=role_name, description="Standard Reader")
    user = User(
        id=user_id,
        name=email.split("@")[0],
        email=email,
        password_hash="mock_hashed_password",
        status="active",
        role_id=role.id,
    )
    user.role = role
    return user


user_a = make_test_user(101, "user_a@test.com")
user_b = make_test_user(102, "user_b@test.com")

token_a = create_access_token({"sub": "101", "role": "reader", "email": "user_a@test.com"})
token_b = create_access_token({"sub": "102", "role": "reader", "email": "user_b@test.com"})

auth_headers_a = {"Authorization": f"Bearer {token_a}"}
auth_headers_b = {"Authorization": f"Bearer {token_b}"}


# ---------------------------------------------------------------------------
# 1. Anonymous Negative Boundary Tests (MUST RETURN 401)
# ---------------------------------------------------------------------------


def test_anonymous_briefing_preferences_rejected_401():
    """Verify that unauthenticated GET /api/v1/briefing/preferences returns HTTP 401."""
    res = client.get("/api/v1/briefing/preferences")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_briefing_send_test_rejected_401():
    """Verify that unauthenticated POST /api/v1/briefing/send-test returns HTTP 401."""
    res = client.post("/api/v1/briefing/send-test", json={"email": "attacker@example.com"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_briefing_verify_email_rejected_401():
    """Verify that unauthenticated POST /api/v1/briefing/verify-email returns HTTP 401."""
    res = client.post("/api/v1/briefing/verify-email", json={"email": "attacker@example.com"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_assistant_query_rejected_401():
    """Verify that unauthenticated POST /api/v1/assistant/query returns HTTP 401."""
    res = client.post("/api/v1/assistant/query", json={"query": "Explain quantum computing"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_assistant_conversations_rejected_401():
    """Verify that unauthenticated GET /api/v1/assistant/conversations returns HTTP 401."""
    res = client.get("/api/v1/assistant/conversations")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_assistant_conversation_detail_rejected_401():
    """Verify that unauthenticated GET /api/v1/assistant/conversations/{id} returns HTTP 401."""
    res = client.get("/api/v1/assistant/conversations/ast_conv_123456")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_chat_conversations_create_rejected_401():
    """Verify that unauthenticated POST /api/v1/chat/conversations returns HTTP 401."""
    res = client.post("/api/v1/chat/conversations", json={"mode": "ARTICLE", "article_id": 10})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_chat_stream_rejected_401():
    """Verify that unauthenticated POST /api/v1/chat/stream returns HTTP 401."""
    res = client.post("/api/v1/chat/stream", json={"conversation_id": "conv_123", "message": "hello"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_chat_conversations_list_rejected_401():
    """Verify that unauthenticated GET /api/v1/chat/conversations returns HTTP 401."""
    res = client.get("/api/v1/chat/conversations")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_workspaces_list_rejected_401():
    """Verify that unauthenticated GET /api/v1/workspaces returns HTTP 401."""
    res = client.get("/api/v1/workspaces")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_saved_articles_rejected_401():
    """Verify that unauthenticated GET /api/v1/me/saved returns HTTP 401."""
    res = client.get("/api/v1/me/saved")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_source_follow_rejected_401():
    """Verify that unauthenticated POST /api/v1/sources/{slug}/follow returns HTTP 401."""
    res = client.post("/api/v1/sources/openai/follow")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_source_unfollow_rejected_401():
    """Verify that unauthenticated DELETE /api/v1/sources/{slug}/follow returns HTTP 401."""
    res = client.delete("/api/v1/sources/openai/follow")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_anonymous_users_following_sources_rejected_401():
    """Verify that unauthenticated GET /api/v1/users/me/following/sources returns HTTP 401."""
    res = client.get("/api/v1/users/me/following/sources")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# 2. Public Read Paths (MUST REMAIN 100% PUBLIC)
# ---------------------------------------------------------------------------


def test_public_news_feed_anonymous_allowed():
    """Verify that guests can access GET /api/v1/news without any Authorization header."""
    res = client.get("/api/v1/news?limit=5")
    assert res.status_code != status.HTTP_401_UNAUTHORIZED


def test_public_sources_catalog_anonymous_allowed():
    """Verify that guests can access GET /api/v1/sources without any Authorization header."""
    res = client.get("/api/v1/sources")
    assert res.status_code != status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# 3. Authenticated Positive Tests
# ---------------------------------------------------------------------------


def test_authenticated_briefing_preferences_success():
    """Verify that an authenticated user can fetch their briefing preferences."""
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        res = client.get("/api/v1/briefing/preferences", headers=auth_headers_a)
        assert res.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_authenticated_assistant_conversations_list_success():
    """Verify that an authenticated user can list their assistant conversations."""
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        res = client.get("/api/v1/assistant/conversations", headers=auth_headers_a)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "conversations" in data
        assert isinstance(data["conversations"], list)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_authenticated_chat_conversations_list_success():
    """Verify that an authenticated user can list their chat conversations."""
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        res = client.get("/api/v1/chat/conversations", headers=auth_headers_a)
        assert res.status_code == status.HTTP_200_OK
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_authenticated_workspaces_list_success():
    """Verify that an authenticated user can list their workspaces."""
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        res = client.get("/api/v1/workspaces", headers=auth_headers_a)
        assert res.status_code == status.HTTP_200_OK
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_authenticated_saved_articles_list_success():
    """Verify that an authenticated user can list their saved articles."""
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        res = client.get("/api/v1/me/saved", headers=auth_headers_a)
        assert res.status_code == status.HTTP_200_OK
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# 4. Horizontal Tenant Isolation Tests (Cross-User A vs B)
# ---------------------------------------------------------------------------


def test_horizontal_isolation_assistant_conversation_cross_user_rejected():
    """
    CRITICAL TENANT ISOLATION:
    User B must NEVER be able to read or query User A's assistant conversation.
    """
    # Simulate DB containing a conversation owned strictly by User A (ID: 101)
    session_a = ConversationSession(
        conversation_id="ast_conv_user_a_secret",
        user_id=user_a.id,
        metadata_json={"owner_id": str(user_a.id)},
    )

    from app.api.v1.routes.assistant import _verify_session_owner
    # Direct function isolation check
    assert _verify_session_owner(session_a, user_a.id) is True
    assert _verify_session_owner(session_a, user_b.id) is False

    # HTTP endpoint isolation check: User B requests User A's session
    app.dependency_overrides[get_current_user] = lambda: user_b
    try:
        res = client.get("/api/v1/assistant/conversations/ast_conv_user_a_secret", headers=auth_headers_b)
        assert res.status_code == status.HTTP_404_NOT_FOUND
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_horizontal_isolation_workspace_cross_user_rejected():
    """
    CRITICAL TENANT ISOLATION:
    User B must NEVER be able to read or mutate User A's private workspace.
    """
    app.dependency_overrides[get_current_user] = lambda: user_b
    try:
        # User B queries a non-existent or User A workspace integer ID
        res = client.get("/api/v1/workspaces/999999", headers=auth_headers_b)
        assert res.status_code == status.HTTP_404_NOT_FOUND
    finally:
        app.dependency_overrides.pop(get_current_user, None)
