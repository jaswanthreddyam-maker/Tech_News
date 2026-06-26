import sys
from urllib.parse import urlparse
import pytest
import pytest_asyncio

from app.core.config import settings
from app.core.database import async_engine
from app.core.shutdown import shutdown_event

import os
db_name = urlparse(settings.DATABASE_URL).path.lstrip("/")
if db_name != "tech_news_today_test":
    if os.environ.get("CHAOS_RUNNER") != "0":
        pytest.exit(
            "❌ Refusing to run tests. Tests cannot run against development database.",
            returncode=1,
        )


@pytest.fixture(autouse=True)
def reset_shutdown_event():
    """Ensure shutdown_event is clear before each test.
    Prevents one test (e.g. test_shutdown) from leaving it set for the next."""
    shutdown_event.clear()
    yield
    shutdown_event.clear()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_database_connections():
    yield
    # Cleanly dispose of the connection pool.
    # This prevents the "Future attached to a different loop" error between tests.
    try:
        await async_engine.dispose()
    except Exception:
        pass


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    import asyncpg
    from urllib.parse import urlparse
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine
    from app.core.config import settings

    parsed = urlparse(settings.DATABASE_URL)
    # Connect to the default 'postgres' database to create the test DB
    sys_url = settings.DATABASE_URL.replace(parsed.path, "/postgres").replace("+asyncpg", "")
    
    try:
        conn = await asyncpg.connect(sys_url)
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='tech_news_today_test'")
        if not exists:
            await conn.execute("CREATE DATABASE tech_news_today_test")
        await conn.close()
    except Exception as e:
        pass # The DB might already exist or the user lacks permission; alembic will catch the real error

    # Run alembic upgrade head programmatically via CLI to use native asyncpg config
    import subprocess
    import os
    env = os.environ.copy()
    env["DATABASE_URL"] = settings.DATABASE_URL
    try:
        import sys
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode())
        raise


@pytest_asyncio.fixture(autouse=True)
async def clean_db_tables():
    """Truncate all data tables before each test to prevent cross-test leakage."""
    import logging
    from sqlalchemy import text
    from app.core.database import async_engine

    try:
        async with async_engine.begin() as conn:
            # Dynamically fetch all public tables except alembic_version and static reference data
            result = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename NOT IN ('alembic_version', 'roles', 'permissions', 'role_permissions', 'categories')"
            ))
            tables = [row[0] for row in result.fetchall()]
            if tables:
                table_list = ", ".join(tables)
                await conn.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
    except Exception as e:
        logging.getLogger("pytest").error(f"Truncate failed: {e}")
    yield


@pytest_asyncio.fixture(autouse=True)
async def reset_redis_client():
    """Reset the global Redis client and data between tests to prevent closed event loop errors."""
    from app.core import redis

    r = redis.get_redis_client()
    await r.flushdb()
    redis.redis_client = None
    yield
    redis.redis_client = None


@pytest_asyncio.fixture
async def db_session():
    """Provide a rollback-protected database session for integration tests."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def auth_headers():
    """
    Create an ephemeral test user in the DB and return Bearer auth headers.

    This fixture exists to supply valid authentication for integration tests that
    call endpoints now protected by ``get_current_user``. The user is inserted
    into the real DB (not a mock) so that the full JWT→DB lookup path succeeds.
    The ``clean_db_tables`` autouse fixture is NOT responsible for cleaning users,
    so we clean up explicitly in the teardown.
    """
    import uuid

    from app.core.database import AsyncSessionLocal
    from app.core.security import create_access_token
    from app.models.user import User

    unique_email = f"test-auth-{uuid.uuid4().hex[:8]}@test.local"

    async with AsyncSessionLocal() as session:
        test_user = User(
            name="Test Auth User",
            email=unique_email,
            status="active",
        )
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)
        user_id = test_user.id

    token = create_access_token(data={"sub": str(user_id), "role": "test"})
    headers = {"Authorization": f"Bearer {token}"}

    yield headers

    # Teardown: remove the ephemeral test user
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            await session.delete(user)
            await session.commit()


# ---------------------------------------------------------------------------
# Session-scoped JWT fixtures for test_api_security.py
#
# Users are created once per test session and tokens minted once.
# Teardown deletes DB records explicitly.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def valid_user_token(clean_db_tables):
    """Active user, no special permissions. Used for 200 assertions on get_current_user endpoints."""
    import uuid

    from app.core.database import AsyncSessionLocal
    from app.core.security import create_access_token
    from app.models.user import User

    email = f"sec-valid-{uuid.uuid4().hex[:8]}@test.local"
    async with AsyncSessionLocal() as session:
        user = User(name="Sec Valid User", email=email, status="active")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    token = create_access_token(data={"sub": str(user_id), "role": "reader", "permissions": []})
    yield token

    async with AsyncSessionLocal() as session:
        u = await session.get(User, user_id)
        if u:
            await session.delete(u)
            await session.commit()


@pytest_asyncio.fixture(scope="function")
async def expired_user_token(clean_db_tables):
    """User exists, but JWT is expired → 401."""
    import uuid
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    email = f"sec-exp-{uuid.uuid4().hex[:8]}@test.local"
    async with AsyncSessionLocal() as session:
        user = User(name="Sec Expired User", email=email, status="active")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": "reader",
        "permissions": [],
        "iat": now,
        "exp": now - timedelta(seconds=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    yield token

    async with AsyncSessionLocal() as session:
        u = await session.get(User, user_id)
        if u:
            await session.delete(u)
            await session.commit()


@pytest_asyncio.fixture(scope="function")
async def admin_token(clean_db_tables):
    """Admin user with FULL_ADMIN permissions → 200 for admin endpoints."""
    import uuid

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.security import create_access_token
    from app.models.user import Permission, Role, RolePermission, User

    async with AsyncSessionLocal() as session:
        # Resolve or create full_admin permission row
        perm_result = await session.execute(select(Permission).where(Permission.name == "full_admin"))
        perm = perm_result.scalars().first()
        if perm is None:
            perm = Permission(name="full_admin", description="Full admin access")
            session.add(perm)
            await session.flush()

        role_name = f"test-admin-role-{uuid.uuid4().hex[:6]}"
        role = Role(name=role_name, description="Security test admin role")
        session.add(role)
        await session.flush()

        session.add(RolePermission(role_id=role.id, permission_id=perm.id))
        await session.flush()

        email = f"sec-admin-{uuid.uuid4().hex[:8]}@test.local"
        user = User(name="Sec Admin User", email=email, status="active", role_id=role.id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id, role_id = user.id, role.id

    token = create_access_token(
        data={"sub": str(user_id), "role": role_name, "permissions": ["full_admin"]}
    )
    yield token

    async with AsyncSessionLocal() as session:
        u = await session.get(User, user_id)
        if u:
            await session.delete(u)
            await session.flush()
        r = await session.get(Role, role_id)
        if r:
            await session.delete(r)
        await session.commit()


@pytest_asyncio.fixture(scope="function")
async def non_admin_token(clean_db_tables):
    """Active user but lacks FULL_ADMIN permissions → 403."""
    import uuid

    from app.core.database import AsyncSessionLocal
    from app.core.security import create_access_token
    from app.models.user import User

    email = f"sec-nonadmin-{uuid.uuid4().hex[:8]}@test.local"
    async with AsyncSessionLocal() as session:
        user = User(name="Sec Non-Admin User", email=email, status="active")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    token = create_access_token(data={"sub": str(user_id), "role": "reader", "permissions": []})
    yield token

    async with AsyncSessionLocal() as session:
        u = await session.get(User, user_id)
        if u:
            await session.delete(u)
            await session.commit()
