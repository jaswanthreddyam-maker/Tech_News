import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.models.user import Permission, RolePermission, User

logger = logging.getLogger("tech_news.security")

# ---------------------------------------------------------------------------
# Password Hashing (bcrypt)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with auto-generated salt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------


async def apply_rate_limit(
    request: Request, action: str, max_requests: int, window_seconds: int = 60, identifier: str | None = None
) -> None:
    """
    Redis-backed rate limiter. Limits requests per IP (and optionally a secondary identifier like email)
    for a specific action within a time window. Raises HTTP 429 if limit is exceeded.
    """
    ip = request.client.host if request.client else "unknown"
    key_suffix = f"{ip}:{identifier}" if identifier else ip
    redis_key = f"rate_limit:{action}:{key_suffix}"

    try:
        r = get_redis_client()
        current = await r.get(redis_key)
        if current and int(current) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
            )

        pipe = r.pipeline()
        pipe.incr(redis_key)
        if not current:
            pipe.expire(redis_key, window_seconds)
        await pipe.execute()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Rate limiting check failed (Redis error): {e}")


# ---------------------------------------------------------------------------
# JWT Token Operations
# ---------------------------------------------------------------------------


def create_access_token(data: dict) -> str:
    """
    Create a signed JWT access token.
    Expects data to contain: sub (user_id as str), role, permissions.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token() -> str:
    """Generate a cryptographically secure random refresh token."""
    return secrets.token_hex(64)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.
    Raises HTTPException 401 on any failure (expired, invalid signature, malformed).
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Redis Permission Cache
# ---------------------------------------------------------------------------


async def get_cached_permissions(user_id: int) -> list[str] | None:
    """Retrieve cached permission list from Redis for the given user."""
    try:
        client = get_redis_client()
        cache_key = f"user:permissions:{user_id}"
        cached = await client.get(cache_key)
        if cached is not None:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.warning(f"Redis permission cache GET failed for user {user_id}: {e}")
        return None


async def cache_user_permissions(user_id: int, permissions: list[str]) -> None:
    """Cache user permissions in Redis with 1-hour TTL."""
    try:
        client = get_redis_client()
        cache_key = f"user:permissions:{user_id}"
        await client.set(cache_key, json.dumps(permissions), ex=3600)
    except Exception as e:
        logger.warning(f"Redis permission cache SET failed for user {user_id}: {e}")


async def clear_permission_cache(user_id: int) -> None:
    """Delete cached permissions for a user from Redis."""
    try:
        client = get_redis_client()
        cache_key = f"user:permissions:{user_id}"
        await client.delete(cache_key)
    except Exception as e:
        logger.warning(f"Redis permission cache DEL failed for user {user_id}: {e}")


# ---------------------------------------------------------------------------
# Permission Loading Helper
# ---------------------------------------------------------------------------


async def _load_user_permissions(db: AsyncSession, user_id: int, role_id: int | None) -> list[str]:
    """Load permissions from DB for a user's role, then cache them."""
    if role_id is None:
        return []

    stmt = (
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    result = await db.execute(stmt)
    permissions = [row[0] for row in result.all()]

    # Cache in Redis for subsequent requests
    await cache_user_permissions(user_id, permissions)
    return permissions


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract Bearer token from Authorization header, decode JWT,
    and load the corresponding User from the database.
    Raises 401 if token is missing, invalid, or user does not exist.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ", 1)[1]
    payload = decode_access_token(token)

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: malformed subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).options(selectinload(User.role)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Access denied.",
        )

    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Extract Bearer token and return User if valid, otherwise return None.
    Does not raise exceptions for missing or invalid tokens.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except HTTPException:
        return None

    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return None

    stmt = select(User).options(selectinload(User.role)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None or user.status != "active":
        return None

    return user


def require_role(*role_names: str):
    """
    DEPRECATED: Use require_permission instead.
    Returns a FastAPI dependency that enforces the current user has one of
    the specified role names. Raises 403 if the user's role is not included.
    """

    async def _role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role is None or current_user.role.name not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {', '.join(role_names)}.",
            )
        return current_user

    return _role_checker


from app.core.permissions import Permission as PermissionEnum


def require_permission(permission_name: PermissionEnum | str):
    """
    Returns a FastAPI dependency that checks whether the current user
    has the specified permission. Uses Redis cache first, then falls
    back to DB lookup + cache population. Raises 403 if permission missing.
    Automatically grants access to super_admin users.
    """

    async def _permission_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        # Try Redis cache first
        permissions = await get_cached_permissions(current_user.id)

        if permissions is None:
            # Fallback to DB and populate cache
            permissions = await _load_user_permissions(db, current_user.id, current_user.role_id)

        if current_user.role and current_user.role.name == "super_admin":
            return current_user

        perm_str = permission_name.value if isinstance(permission_name, PermissionEnum) else permission_name

        if perm_str not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {perm_str}.",
            )

        return current_user

    return _permission_checker
