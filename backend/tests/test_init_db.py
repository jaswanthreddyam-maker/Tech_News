import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.init_db import main as init_db_main
from app.core.security import verify_password
from app.models.growth import FeatureFlag
from app.models.user import Permission, Role, User


@pytest.mark.asyncio
async def test_init_db_seeding():
    admin_email = settings.ADMIN_EMAIL or settings.INITIAL_ADMIN_EMAIL
    # 0. Clean up any existing admin user to ensure deterministic seeding
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == admin_email))
        await db.commit()

    # 1. Run database initialization
    await init_db_main()

    # 2. Verify admin exists in the database and is set up correctly
    async with AsyncSessionLocal() as db:
        stmt = select(User).options(selectinload(User.role)).where(User.email == admin_email)
        res = await db.execute(stmt)
        user = res.scalars().first()

        assert user is not None
        assert user.email == admin_email
        assert user.status == "active"
        assert user.role is not None
        assert user.role.name == "super_admin"

        # Verify password is valid (plain from settings or default test password)
        admin_password = settings.INITIAL_ADMIN_PASSWORD or "mnbvcxzlkjhgfdsapoiuytrewq"
        assert verify_password(admin_password, user.password_hash) is True


@pytest.mark.asyncio
async def test_init_db_idempotency():
    """
    Running init_db twice must not create duplicate admins, roles,
    permissions, or feature flags. Very common regression.
    """
    admin_email = settings.ADMIN_EMAIL or settings.INITIAL_ADMIN_EMAIL
    # 0. Clean slate
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == admin_email))
        await db.commit()

    # 1. First run — seeds everything
    await init_db_main()

    async with AsyncSessionLocal() as db:
        admin_count_1 = (await db.execute(select(func.count(User.id)).where(User.email == admin_email))).scalar()
        role_count_1 = (await db.execute(select(func.count(Role.id)))).scalar()
        perm_count_1 = (await db.execute(select(func.count(Permission.id)))).scalar()
        flag_count_1 = (await db.execute(select(func.count(FeatureFlag.id)))).scalar()

    assert admin_count_1 == 1, f"Expected 1 admin after first run, got {admin_count_1}"

    # 2. Second run — must be a no-op for all seed data
    await init_db_main()

    async with AsyncSessionLocal() as db:
        admin_count_2 = (await db.execute(select(func.count(User.id)).where(User.email == admin_email))).scalar()
        role_count_2 = (await db.execute(select(func.count(Role.id)))).scalar()
        perm_count_2 = (await db.execute(select(func.count(Permission.id)))).scalar()
        flag_count_2 = (await db.execute(select(func.count(FeatureFlag.id)))).scalar()

    # Still exactly one admin
    assert admin_count_2 == 1, f"Expected 1 admin after second run, got {admin_count_2}"

    # Counts unchanged — no duplicates
    assert role_count_2 == role_count_1, f"Roles duplicated: {role_count_1} → {role_count_2}"
    assert perm_count_2 == perm_count_1, f"Permissions duplicated: {perm_count_1} → {perm_count_2}"
    assert flag_count_2 == flag_count_1, f"Feature flags duplicated: {flag_count_1} → {flag_count_2}"
