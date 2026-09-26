$env:PATH = "C:\Program Files\Git\cmd;C:\Program Files\Git\bin;" + $env:PATH
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (& git rev-parse --show-toplevel).Trim()
if (-not $repoRoot) { throw 'Not inside a Git repository.' }
Set-Location $repoRoot

$branch = 'security/p0-remediation'
& git fetch origin main
if (& git show-ref --verify --quiet "refs/heads/$branch") {
    & git switch $branch
} else {
    & git switch -c $branch origin/main
}

function Replace-Exact([string]$Path, [string]$Old, [string]$New) {
    $full = Join-Path $repoRoot $Path
    $text = [System.IO.File]::ReadAllText($full)
    # Normalize CRLF/LF for exact matching
    $textNorm = $text -replace "\r\n", "`n"
    $oldNorm = $Old -replace "\r\n", "`n"
    $newNorm = $New -replace "\r\n", "`n"
    if (-not $textNorm.Contains($oldNorm)) {
        throw "Expected block not found in $Path; aborting to avoid an unsafe partial edit."
    }
    $updatedNorm = $textNorm.Replace($oldNorm, $newNorm)
    # Preserve original line endings (CRLF if original had CRLF)
    if ($text.Contains("`r`n")) {
        $finalText = $updatedNorm -replace "(?<!\r)\n", "`r`n"
    } else {
        $finalText = $updatedNorm
    }
    [System.IO.File]::WriteAllText($full, $finalText, [System.Text.UTF8Encoding]::new($false))
}

# P0-1: fail closed on repository-default production secrets.
Replace-Exact 'backend/app/core/config.py' @'
        if app_env == "production":
            # 1. Provide secure fallback for secret key if default dev value was provided
            if self.SECRET_KEY in (
                "supersecretkey_change_me_in_production_32_chars_long",
                "dev_only_super_secure_32_character_secret_key",
                "change_me",
            ):
                logger.warning("Default SECRET_KEY detected in production. Generating secure fallback key.")
                object.__setattr__(self, "SECRET_KEY", "prod_sec_key_9f8b2c4e6d1a3f5b7c9e1d3f5a7b9c1e3f5a7b9c1e3f5a7b9c1e3f5a7b9c1e3")

            # Validate backup keys in production
            if "dev_only" in self.BACKUP_ENCRYPTION_KEY or "encryption_key" in self.BACKUP_ENCRYPTION_KEY:
                object.__setattr__(self, "BACKUP_ENCRYPTION_KEY", "32ByteProdEncryptionKeyForBackups!")

            if "dev_only" in self.BACKUP_SIGNING_KEY or "signing_key" in self.BACKUP_SIGNING_KEY:
                object.__setattr__(self, "BACKUP_SIGNING_KEY", "32ByteProdSigningKeyForBackups!!")

            # 2. Provide secure fallback for JWT secret key if default dev value was provided
            if "phase4_dev" in self.JWT_SECRET_KEY or "change_in_production" in self.JWT_SECRET_KEY:
                logger.warning("Default JWT_SECRET_KEY detected in production. Generating secure fallback key.")
                object.__setattr__(self, "JWT_SECRET_KEY", "prod_jwt_sec_8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e")


            # 3. Prevent wildcard CORS in production
'@ @'
        if app_env == "production":
            # Fail closed when security-critical secrets are missing or still
            # set to repository defaults. Never substitute deterministic keys
            # from source control into a production process.
            default_secret_keys = {
                "supersecretkey_change_me_in_production_32_chars_long",
                "dev_only_super_secure_32_character_secret_key",
                "change_me",
            }
            if not self.SECRET_KEY or self.SECRET_KEY in default_secret_keys:
                raise RuntimeError(
                    "FATAL: SECRET_KEY must be explicitly configured in production."
                )

            if (
                not self.JWT_SECRET_KEY
                or "phase4_dev" in self.JWT_SECRET_KEY
                or "change_in_production" in self.JWT_SECRET_KEY
            ):
                raise RuntimeError(
                    "FATAL: JWT_SECRET_KEY must be explicitly configured in production."
                )

            if not self.BACKUP_ENCRYPTION_KEY or "dev_only" in self.BACKUP_ENCRYPTION_KEY:
                raise RuntimeError(
                    "FATAL: BACKUP_ENCRYPTION_KEY must be explicitly configured in production."
                )

            if not self.BACKUP_SIGNING_KEY or "dev_only" in self.BACKUP_SIGNING_KEY:
                raise RuntimeError(
                    "FATAL: BACKUP_SIGNING_KEY must be explicitly configured in production."
                )

            # 3. Prevent wildcard CORS in production
'@

# P0-2: protect unauthenticated admin diagnostics.
Replace-Exact 'backend/app/api/v1/routes/admin.py' @'
from app.models.source import Source
from app.models.user import AIJobHistory, ArticleRevision, AuditLog, Role, User
'@ @'
from app.models.source import Source
from app.models.telemetry import TimelineNode
from app.models.user import AIJobHistory, ArticleRevision, AuditLog, Role, User
'@
Replace-Exact 'backend/app/api/v1/routes/admin.py' @'
@router.get("/diagnostic/db-truth")
async def get_db_truth(db: AsyncSession = Depends(get_db)):
'@ @'
@router.get("/diagnostic/db-truth")
async def get_db_truth(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
'@
Replace-Exact 'backend/app/api/v1/routes/admin.py' @'
@router.get("/diagnostic/filtered-samples")
async def get_filtered_samples(limit: int = 5, db: AsyncSession = Depends(get_db)):
'@ @'
@router.get("/diagnostic/filtered-samples")
async def get_filtered_samples(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin")),
):
'@

# P0-2b: restrict Redis diagnostics.
Replace-Exact 'backend/main.py' @'
from app.core.redis import close_redis_connection, verify_redis_connection
from app.schemas.responses import ErrorDetails, ErrorResponse
'@ @'
from app.core.redis import close_redis_connection, verify_redis_connection
from app.core.security import require_role
from app.schemas.responses import ErrorDetails, ErrorResponse
'@
Replace-Exact 'backend/main.py' @'
from fastapi import FastAPI, Request, Depends, status
'@ @'
from fastapi import Depends, FastAPI, HTTPException, Request, status
'@
Replace-Exact 'backend/main.py' @'
@app.get("/health/redis-diag", tags=["System"])
async def root_health_redis_diag():
'@ @'
@app.get("/health/redis-diag", tags=["System"])
async def root_health_redis_diag(
    current_user=Depends(require_role("super_admin")),
):
'@
Replace-Exact 'backend/main.py' @'
    from app.core.config import settings

    raw_url = settings.REDIS_URL
'@ @'
    from app.core.config import settings

    if settings.effective_environment == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic endpoint disabled in production.",
        )

    raw_url = settings.REDIS_URL
'@

# P0-3: validate every outbound image request and redirect hop before issuing it.
Replace-Exact 'backend/app/services/ingestion/image_helper.py' @'
logger = logging.getLogger("tech_news.image_helper")


def is_safe_url(url: str) -> bool:
'@ @'
logger = logging.getLogger("tech_news.image_helper")

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5


def is_safe_url(url: str) -> bool:
'@
Replace-Exact 'backend/app/services/ingestion/image_helper.py' @'
        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname to IP addresses
'@ @'
        hostname = parsed.hostname
        if not hostname:
            return False

        # Embedded credentials have no legitimate role in article image URLs.
        if parsed.username or parsed.password:
            return False

        # Resolve hostname to IP addresses
'@

# Insert the shared helper immediately before PRE_SCORING_WEIGHTS.
Replace-Exact 'backend/app/services/ingestion/image_helper.py' @'
        return False


PRE_SCORING_WEIGHTS = {
'@ @'
        return False


async def _request_with_ssrf_protection(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response | None:
    """Request a URL while validating each redirect target before connecting."""
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        if not is_safe_url(current_url):
            logger.warning("Image Helper: SSRF blocked URL: %s", current_url)
            return None

        if method.upper() == "HEAD":
            response = await client.head(
                current_url,
                follow_redirects=False,
                **kwargs,
            )
        else:
            response = await client.get(
                current_url,
                follow_redirects=False,
                **kwargs,
            )

        if response.status_code not in REDIRECT_STATUSES:
            return response

        location = response.headers.get("location")
        if not location:
            return response

        current_url = urljoin(current_url, location)

    logger.warning("Image Helper: redirect limit exceeded for %s", url)
    return None


PRE_SCORING_WEIGHTS = {
'@

Replace-Exact 'backend/app/services/ingestion/image_helper.py' @'
        async with httpx.AsyncClient(timeout=5.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
            resp = await client.head(url)
'@ @'
        async with httpx.AsyncClient(
            timeout=5.0,
            headers=BROWSER_HEADERS,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            resp = await _request_with_ssrf_protection(client, "HEAD", url)
            if resp is None:
                return None
'@
Replace-Exact 'backend/app/services/ingestion/image_helper.py' @'
                resp = await client.get(url, headers=headers)
'@ @'
                resp = await _request_with_ssrf_protection(client, "GET", url, headers=headers)
                if resp is None:
                    return None
'@
Replace-Exact 'backend/app/services/ingestion/image_helper.py' @'
        async with httpx.AsyncClient(timeout=10.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)

            # Verify redirect target URL if redirected
            if str(resp.url) != url and not is_safe_url(str(resp.url)):
                logger.warning(f"Image Helper: SSRF redirect target blocked: {resp.url}")
                return None, None, "ssrf_blocked_redirect", None
'@ @'
        async with httpx.AsyncClient(
            timeout=10.0,
            headers=BROWSER_HEADERS,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            resp = await _request_with_ssrf_protection(client, "GET", url)
            if resp is None:
                return None, None, "ssrf_blocked_redirect", None
'@

# P0-3b: redirect resolution must not blindly follow untrusted destinations.
Replace-Exact 'backend/app/services/ingestion/utils.py' @'
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
'@ @'
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
'@
Replace-Exact 'backend/app/services/ingestion/utils.py' @'
    import httpx

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(3.0, connect=1.5),
            headers={"User-Agent": "TechNewsTodayBot/1.0 (+http://localhost/bot)"},
        ) as client:
            try:
                # 1. Try HEAD first
                resp = await client.head(url)
                if resp.status_code < 400:
                    return str(resp.url)
            except Exception:
                pass

            # 2. Fallback to streaming GET (read headers only, don't download body)
            try:
                async with client.stream("GET", url) as resp:
                    return str(resp.url)
            except Exception:
                pass
    except Exception:
        pass
'@ @'
    import httpx
    from app.services.ingestion.image_helper import is_safe_url

    current_url = url

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(3.0, connect=1.5),
            headers={"User-Agent": "TechNewsTodayBot/1.0 (+http://localhost/bot)"},
            trust_env=False,
        ) as client:
            for _ in range(6):
                if not is_safe_url(current_url):
                    return url

                try:
                    resp = await client.head(current_url, follow_redirects=False)
                    if resp.status_code < 400:
                        location = resp.headers.get("location")
                        if location:
                            current_url = urljoin(current_url, location)
                            continue
                        return str(resp.url)
                except Exception:
                    pass

                try:
                    async with client.stream("GET", current_url, follow_redirects=False) as resp:
                        if resp.status_code in {301, 302, 303, 307, 308}:
                            location = resp.headers.get("location")
                            if location:
                                current_url = urljoin(current_url, location)
                                continue
                        return str(resp.url)
                except Exception:
                    pass
    except Exception:
        pass
'@

& git diff --check
& git status --short
Write-Host "P0 security remediation applied on branch $branch."
Write-Host "Next: run the backend regression suite before committing."
