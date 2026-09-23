import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import log_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.core.redis import get_redis_client
from app.core.security import (
    _load_user_permissions,
    apply_rate_limit,
    create_access_token,
    create_refresh_token,
    get_cached_permissions,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import OAuthAccount, Role, User, UserSession
from app.notifications.email.provider import EmailPayload, get_email_provider
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.responses import StandardResponse

logger = logging.getLogger("tech_news.auth")
router = APIRouter()

# Cookie configuration constants
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/"


def _is_production_or_secure(request: Request | None = None) -> bool:
    """Determine if running in production or a secure HTTPS deployment."""
    app_env = (settings.APP_ENV or settings.ENV or "").lower()
    if app_env in {"production", "staging"} or not settings.DEBUG:
        return True
    if request:
        return (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto", "").lower() == "https"
        )
    return False


def _set_refresh_cookie(
    response: Response,
    token: str,
    max_age: int,
    request: Request | None = None,
) -> None:
    """Set the HttpOnly refresh token cookie on the response."""
    is_secure = _is_production_or_secure(request)
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=max_age,
    )


def _delete_refresh_cookie(response: Response) -> None:
    """Delete the refresh token cookie from the response."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )


def _extract_client_info(request: Request) -> tuple:
    """Extract client IP and User-Agent from the request."""
    ip = request.client.host if request.client else "unknown"
    device = request.headers.get("User-Agent", "unknown")
    return ip, device


async def _build_token_response(
    db: AsyncSession,
    user: User,
    permissions: list[str] | None = None,
) -> TokenResponse:
    """Build a TokenResponse with access token and user summary."""
    if permissions is None:
        permissions = await _load_user_permissions(db, user.id, user.role_id)

    role_name = user.role.name if user.role else "reader"

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "role": role_name,
            "permissions": permissions,
        }
    )

    return TokenResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": role_name,
            "status": user.status,
        },
    )


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


@router.post("/register", response_model=StandardResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account with the 'reader' role.
    Automatically logs in the user and returns an access/refresh token pair.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    ip, device = _extract_client_info(request)

    # Redis-backed Rate Limiter (Max 5 requests per minute per IP)
    try:
        await apply_rate_limit(request, action="register", max_requests=5)
    except HTTPException as e:
        await log_audit(db, "register_rate_limit", "auth", metadata={"ip": ip, "device": device})
        raise e

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalars().first() is not None:
        await log_audit(
            db,
            "register_failed",
            "auth",
            metadata={"reason": "email_exists", "email": payload.email},
            ip_address=ip,
            device=device,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Resolve reader role
    role_result = await db.execute(select(Role).where(Role.name == "reader"))
    reader_role = role_result.scalars().first()
    if reader_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System configuration error: default role not found.",
        )

    # Create user
    hashed = hash_password(payload.password)
    new_user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hashed,
        role_id=reader_role.id,
        status="active",
    )
    db.add(new_user)
    await db.flush()

    # Eagerly load role for token generation
    new_user.role = reader_role

    # Generate session record (Auto-login)
    expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    refresh = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expire_days)

    session_record = UserSession(
        user_id=new_user.id,
        refresh_token=refresh,
        ip_address=ip,
        device=device,
        expires_at=expires_at,
    )
    db.add(session_record)
    await db.flush()

    # Set refresh cookie
    max_age_seconds = expire_days * 24 * 60 * 60
    _set_refresh_cookie(response, refresh, max_age_seconds, request=request)

    # Build token response
    token_response = await _build_token_response(db, new_user)

    await log_audit(
        db,
        "register_success",
        "auth",
        user_id=new_user.id,
        metadata={"email": payload.email, "auth_provider": "local"},
        ip_address=ip,
        device=device,
    )
    await db.commit()
    logger.info(f"New user registered and logged in: {payload.email} (ID: {new_user.id})")

    return StandardResponse(
        correlation_id=correlation_id,
        data=token_response,
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=StandardResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email and password.
    Returns access_token in JSON body and sets refresh_token as HttpOnly cookie.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    ip, device = _extract_client_info(request)

    try:
        await apply_rate_limit(request, action="login", max_requests=10, identifier=payload.email)
    except HTTPException as e:
        await log_audit(db, "login_rate_limit", "auth", metadata={"email": payload.email}, ip_address=ip, device=device)
        raise e

    # Find user by email
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.email == payload.email))
    user = result.scalars().first()

    if user is None or not verify_password(payload.password, user.password_hash or ""):
        # Avoid login enumeration by returning the same error for missing user or wrong password
        if user:
            await log_audit(
                db,
                "login_failed",
                "auth",
                user_id=user.id,
                metadata={"reason": "invalid_password", "email": payload.email},
                ip_address=ip,
                device=device,
            )
        else:
            await log_audit(
                db,
                "login_failed",
                "auth",
                metadata={"reason": "invalid_email", "email": payload.email},
                ip_address=ip,
                device=device,
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.status != "active":
        await log_audit(
            db,
            "login_failed",
            "auth",
            user_id=user.id,
            metadata={"reason": f"account_{user.status}", "email": payload.email},
            ip_address=ip,
            device=device,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Please contact support.",
        )

    # Determine refresh token TTL based on remember_me
    if payload.remember_me:
        expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS * 4  # 28 days
    else:
        expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS  # 7 days

    # Create session record
    refresh = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expire_days)

    session_record = UserSession(
        user_id=user.id,
        refresh_token=refresh,
        ip_address=ip,
        device=device,
        expires_at=expires_at,
    )
    db.add(session_record)
    await db.flush()

    # Set refresh cookie
    max_age_seconds = expire_days * 24 * 60 * 60
    _set_refresh_cookie(response, refresh, max_age_seconds, request=request)

    # Build token response
    token_response = await _build_token_response(db, user)

    await log_audit(
        db,
        "login_success",
        "auth",
        user_id=user.id,
        metadata={"email": user.email, "auth_provider": "local"},
        ip_address=ip,
        device=device,
    )
    await db.commit()
    logger.info(f"User logged in: {user.email} (ID: {user.id}) from {ip}")

    return StandardResponse(
        correlation_id=correlation_id,
        data=token_response,
    )


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=StandardResponse[TokenResponse])
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate the refresh token. Reads current token from cookies,
    validates it, revokes the old session, creates a new one,
    and returns a fresh access_token.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    ip, device = _extract_client_info(request)

    try:
        await apply_rate_limit(request, action="token_refresh", max_requests=20)
    except HTTPException as e:
        await log_audit(db, "refresh_rate_limit", "auth", ip_address=ip, device=device)
        raise e

    # Read refresh token from cookies
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    # Find session
    result = await db.execute(select(UserSession).where(UserSession.refresh_token == token))
    session_record = result.scalars().first()

    if session_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    if session_record.revoked_at is not None:
        # Replay attack detection: if this token was revoked specifically due to a rotation, it means an old token is being reused.
        if session_record.revocation_reason == "token_rotation":
            logger.warning(
                f"Replay attack detected! Token for session {session_record.id} reused after rotation. Revoking all sessions for user."
            )
            active_sessions_result = await db.execute(
                select(UserSession).where(
                    UserSession.user_id == session_record.user_id, UserSession.revoked_at.is_(None)
                )
            )
            for active_session in active_sessions_result.scalars().all():
                active_session.revoked_at = datetime.now(timezone.utc)
                active_session.revocation_reason = "compromised_token_replay"
            await db.flush()
            await log_audit(
                db,
                "token_replay_detected",
                "auth",
                user_id=session_record.user_id,
                metadata={"session_id": session_record.id},
                ip_address=ip,
                device=device,
            )
            _delete_refresh_cookie(response)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked.",
        )

    if session_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired.",
        )

    # Load user
    user_result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == session_record.user_id)
    )
    user = user_result.scalars().first()

    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
        )

    # Revoke old session
    session_record.revoked_at = datetime.now(timezone.utc)
    session_record.revocation_reason = "token_rotation"

    # Create new session with same remaining TTL
    new_refresh = create_refresh_token()
    remaining_ttl = session_record.expires_at - datetime.now(timezone.utc)
    new_expires_at = datetime.now(timezone.utc) + remaining_ttl

    new_session = UserSession(
        user_id=user.id,
        refresh_token=new_refresh,
        ip_address=ip,
        device=device,
        expires_at=new_expires_at,
    )
    db.add(new_session)
    await db.flush()

    # Set new cookie
    remaining_seconds = max(int(remaining_ttl.total_seconds()), 0)
    _set_refresh_cookie(response, new_refresh, remaining_seconds, request=request)

    # Build new access token
    token_response = await _build_token_response(db, user)

    await log_audit(
        db,
        "refresh_success",
        "auth",
        user_id=user.id,
        metadata={"session_id": new_session.id},
        ip_address=ip,
        device=device,
    )
    await db.commit()
    logger.info(f"Token refreshed for user: {user.email} (ID: {user.id})")

    return StandardResponse(
        correlation_id=correlation_id,
        data=token_response,
    )


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------


@router.post("/logout", response_model=StandardResponse[dict])
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Log out the current session by revoking the refresh token and deleting the cookie.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if token:
        result = await db.execute(select(UserSession).where(UserSession.refresh_token == token))
        session_record = result.scalars().first()
        if session_record and session_record.revoked_at is None:
            session_record.revoked_at = datetime.now(timezone.utc)
            session_record.revocation_reason = "user_logout"
            await db.flush()
            await db.commit()

    _delete_refresh_cookie(response)

    return StandardResponse(
        correlation_id=correlation_id,
        data={"message": "Successfully logged out."},
    )


# ---------------------------------------------------------------------------
# POST /logout-all
# ---------------------------------------------------------------------------


@router.post("/logout-all", response_model=StandardResponse[dict])
async def logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke ALL active sessions for the authenticated user across all devices.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
        )
    )
    active_sessions = result.scalars().all()
    revoked_count = 0

    for session_rec in active_sessions:
        session_rec.revoked_at = datetime.now(timezone.utc)
        session_rec.revocation_reason = "logout_all_devices"
        revoked_count += 1

    await db.flush()
    await db.commit()
    _delete_refresh_cookie(response)

    logger.info(f"User {current_user.email} logged out of all {revoked_count} sessions.")

    return StandardResponse(
        correlation_id=correlation_id,
        data={
            "message": f"Successfully revoked {revoked_count} active session(s).",
            "sessions_revoked": revoked_count,
        },
    )


# ---------------------------------------------------------------------------
# POST /google
# ---------------------------------------------------------------------------


@router.post("/google", response_model=StandardResponse[TokenResponse])
async def google_auth(
    payload: GoogleAuthRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Google OAuth endpoint. Requires a valid GOOGLE_CLIENT_ID configuration.
    Validates token, resolves/creates user, and returns identical JWT to normal login.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    ip, device = _extract_client_info(request)

    if not settings.GOOGLE_CLIENT_ID or "placeholder" in settings.GOOGLE_CLIENT_ID.lower():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Google OAuth is not configured. A valid GOOGLE_CLIENT_ID must be "
                "set in the environment to enable Google sign-in."
            ),
        )

    try:
        await apply_rate_limit(request, action="google_login", max_requests=10)
    except HTTPException as e:
        await log_audit(db, "google_rate_limit", "auth", ip_address=ip, device=device)
        raise e

    id_info = None
    # Support both Google ID token (JWT) and OAuth2 access token (ya29...)
    if payload.credential.startswith("ya29.") or payload.credential.count(".") != 2:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {payload.credential}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    id_info = {
                        "iss": "https://accounts.google.com",
                        "email_verified": data.get("email_verified", True),
                        "email": data.get("email"),
                        "sub": data.get("sub"),
                        "name": data.get("name", "Google User"),
                        "given_name": data.get("given_name"),
                        "family_name": data.get("family_name"),
                        "picture": data.get("picture"),
                    }
                else:
                    await log_audit(
                        db, "google_login_failed", "auth", metadata={"reason": "invalid_access_token"}, ip_address=ip, device=device
                    )
                    raise HTTPException(status_code=401, detail="Invalid Google access token.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Failed to verify Google access token: {e}")
    else:
        try:
            id_info = id_token.verify_oauth2_token(payload.credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
        except ValueError as e:
            await log_audit(
                db, "google_login_failed", "auth", metadata={"reason": "invalid_token"}, ip_address=ip, device=device
            )
            raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {e}")

    if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
        await log_audit(
            db, "google_login_failed", "auth", metadata={"reason": "invalid_issuer"}, ip_address=ip, device=device
        )
        raise HTTPException(status_code=401, detail="Invalid issuer.")

    if not id_info.get("email_verified"):
        await log_audit(
            db, "google_login_failed", "auth", metadata={"reason": "email_not_verified"}, ip_address=ip, device=device
        )
        raise HTTPException(status_code=401, detail="Google email not verified.")

    email = id_info.get("email")
    sub = id_info.get("sub")
    name = id_info.get("name", "Google User")
    given_name = id_info.get("given_name")
    family_name = id_info.get("family_name")
    picture = id_info.get("picture")

    if not email or not sub:
        raise HTTPException(status_code=400, detail="Incomplete Google profile payload.")

    result = await db.execute(
        select(OAuthAccount)
        .options(selectinload(OAuthAccount.user).selectinload(User.role))
        .where(OAuthAccount.provider == "google", OAuthAccount.provider_user_id == sub)
    )
    oauth_account = result.scalars().first()

    if oauth_account:
        user = oauth_account.user
    else:
        user_result = await db.execute(select(User).options(selectinload(User.role)).where(User.email == email))
        user = user_result.scalars().first()

        if user:
            new_oauth = OAuthAccount(user_id=user.id, provider="google", provider_user_id=sub)
            db.add(new_oauth)
        else:
            admin_email = getattr(settings, "GOOGLE_ADMIN_EMAIL", "").lower().strip()
            role_name = "admin" if email.lower().strip() == admin_email else "reader"

            role_result = await db.execute(select(Role).where(Role.name == role_name))
            assigned_role = role_result.scalars().first()

            user = User(
                email=email,
                name=name,
                password_hash=None,
                role_id=assigned_role.id if assigned_role else None,
                status="active",
            )
            db.add(user)
            await db.flush()
            user.role = assigned_role

            new_oauth = OAuthAccount(user_id=user.id, provider="google", provider_user_id=sub)
            db.add(new_oauth)

    user.name = name
    if given_name:
        user.given_name = given_name
    if family_name:
        user.family_name = family_name
    if picture:
        user.profile_picture = picture
    user.last_login = datetime.now(timezone.utc)

    await db.flush()

    expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    refresh = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expire_days)

    session_record = UserSession(
        user_id=user.id,
        refresh_token=refresh,
        ip_address=ip,
        device=device,
        expires_at=expires_at,
    )
    db.add(session_record)
    await db.flush()

    max_age_seconds = expire_days * 24 * 60 * 60
    _set_refresh_cookie(response, refresh, max_age_seconds, request=request)

    token_response = await _build_token_response(db, user)

    await log_audit(
        db,
        "google_login_success",
        "auth",
        user_id=user.id,
        metadata={"email": user.email, "auth_provider": "google"},
        ip_address=ip,
        device=device,
    )
    await db.commit()
    logger.info(f"User logged in via Google: {user.email} (ID: {user.id})")

    return StandardResponse(
        correlation_id=correlation_id,
        data=token_response,
    )


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


@router.get("/me", response_model=StandardResponse[UserResponse])
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the authenticated user's profile including role and permissions.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    # Load permissions (Redis cache → DB fallback)
    permissions = await get_cached_permissions(current_user.id)
    if permissions is None:
        permissions = await _load_user_permissions(db, current_user.id, current_user.role_id)

    role_name = current_user.role.name if current_user.role else None

    user_response = UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=role_name,
        permissions=permissions,
        status=current_user.status,
    )

    return StandardResponse(
        correlation_id=correlation_id,
        data=user_response,
    )


# ---------------------------------------------------------------------------
# POST /forgot-password
# ---------------------------------------------------------------------------


PASSWORD_RESET_PREFIX = "password_reset:"
PASSWORD_RESET_TTL = 900  # 15 minutes


def _hash_otp(code: str) -> str:
    """SHA-256 hash the OTP code so it's not stored in plaintext in Redis."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@router.post("/forgot-password", response_model=StandardResponse[dict])
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset OTP code. Sends a 6-digit code to the user's email.
    Always returns success to prevent email enumeration.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    ip, device = _extract_client_info(request)

    # Rate limit: 3 requests per minute per IP
    try:
        await apply_rate_limit(request, action="forgot_password", max_requests=3)
    except HTTPException as e:
        await log_audit(db, "forgot_password_rate_limit", "auth", metadata={"ip": ip}, ip_address=ip, device=device)
        raise e

    email = payload.email.lower().strip()

    # Generate 6-digit OTP
    otp_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    hashed_code = _hash_otp(otp_code)

    # Store hashed OTP in Redis with 15-minute TTL
    try:
        redis = get_redis_client()
        redis_key = f"{PASSWORD_RESET_PREFIX}{email}"
        await redis.set(redis_key, hashed_code, ex=PASSWORD_RESET_TTL)
    except Exception as e:
        logger.error(f"Redis error storing password reset OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process password reset request. Please try again.",
        )

    # Check if user exists (but always return success for anti-enumeration)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if user:
        # Send OTP via email
        try:
            provider = get_email_provider()
            email_payload = EmailPayload(
                to=email,
                subject="Your Password Reset Code — Tech News Today",
                html=(
                    f'<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 24px; background: #080808; color: #ffffff;">'
                    f'<h1 style="font-size: 24px; font-weight: 800; letter-spacing: -0.5px; margin: 0 0 8px;">TECH NEWS TODAY</h1>'
                    f'<p style="font-size: 11px; letter-spacing: 2px; color: #888; text-transform: uppercase; margin: 0 0 32px;">Password Reset Request</p>'
                    f'<p style="font-size: 14px; color: #ccc; line-height: 1.6; margin: 0 0 24px;">Use the following code to reset your password. This code expires in 15 minutes.</p>'
                    f'<div style="background: #111; border: 1px solid #222; padding: 20px; text-align: center; margin: 0 0 24px;">'
                    f'<span style="font-family: monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #fff;">{otp_code}</span>'
                    f'</div>'
                    f'<p style="font-size: 12px; color: #666; line-height: 1.5;">If you did not request this reset, you can safely ignore this email. Your password will not be changed.</p>'
                    f'</div>'
                ),
                text=f"Your Tech News Today password reset code is: {otp_code}\n\nThis code expires in 15 minutes. If you did not request this, ignore this email.",
                idempotency_key=f"pwd-reset-{email}-{correlation_id}",
                tags={"category": "password_reset"},
            )
            await provider.send(email_payload)
            logger.info(f"Password reset OTP sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}")
            # Don't expose email delivery failures to the client

        await log_audit(
            db,
            "forgot_password_requested",
            "auth",
            user_id=user.id,
            metadata={"email": email},
            ip_address=ip,
            device=device,
        )
    else:
        await log_audit(
            db,
            "forgot_password_unknown_email",
            "auth",
            metadata={"email": email},
            ip_address=ip,
            device=device,
        )

    # Always return success to prevent email enumeration
    return StandardResponse(
        correlation_id=correlation_id,
        data={"message": "If an account exists with this email, a reset code has been sent."},
    )


# ---------------------------------------------------------------------------
# POST /reset-password
# ---------------------------------------------------------------------------


@router.post("/reset-password", response_model=StandardResponse[dict])
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete a password reset using a 6-digit OTP code.
    Verifies the OTP, updates the password hash, and revokes all existing sessions.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    ip, device = _extract_client_info(request)

    # Rate limit: 5 attempts per minute per IP
    try:
        await apply_rate_limit(request, action="reset_password", max_requests=5)
    except HTTPException as e:
        await log_audit(db, "reset_password_rate_limit", "auth", metadata={"ip": ip}, ip_address=ip, device=device)
        raise e

    email = payload.email.lower().strip()
    submitted_hash = _hash_otp(payload.code.strip())

    # Verify OTP from Redis
    try:
        redis = get_redis_client()
        redis_key = f"{PASSWORD_RESET_PREFIX}{email}"
        stored_hash = await redis.get(redis_key)
    except Exception as e:
        logger.error(f"Redis error verifying password reset OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to verify reset code. Please try again.",
        )

    if not stored_hash or stored_hash != submitted_hash:
        await log_audit(
            db,
            "reset_password_invalid_code",
            "auth",
            metadata={"email": email},
            ip_address=ip,
            device=device,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code. Please request a new one.",
        )

    # Find user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code. Please request a new one.",
        )

    # Update password hash
    user.password_hash = hash_password(payload.new_password)
    await db.flush()

    # Delete the used OTP from Redis
    try:
        await redis.delete(redis_key)
    except Exception:
        pass  # Non-critical: OTP will expire naturally

    # Revoke all active sessions for security
    sessions_result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
    )
    for session_rec in sessions_result.scalars().all():
        session_rec.revoked_at = datetime.now(timezone.utc)
        session_rec.revocation_reason = "password_reset"
    await db.flush()

    await log_audit(
        db,
        "reset_password_success",
        "auth",
        user_id=user.id,
        metadata={"email": email},
        ip_address=ip,
        device=device,
    )
    await db.commit()
    logger.info(f"Password reset completed for user: {email} (ID: {user.id})")

    return StandardResponse(
        correlation_id=correlation_id,
        data={"message": "Password has been reset successfully. You can now sign in with your new password."},
    )
