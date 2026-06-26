from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.redis import get_redis_client

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MAINTENANCE_BYPASS_PREFIXES = ("/api/v1/backup",)


def is_maintenance_bypass(path: str) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in MAINTENANCE_BYPASS_PREFIXES)


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """
    Fast-fail state-changing API requests while maintenance mode is active.

    Read-only routes remain available by method, including health checks, metrics,
    and SSE streams. Backup/restore routes are explicitly bypassed so operators
    can complete recovery workflows while the write lock is active.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method in WRITE_METHODS:
            try:
                redis_client = get_redis_client()
                if redis_client:
                    is_maintenance = await redis_client.get("settings:maintenance_mode")
                    if is_maintenance == b"1" or is_maintenance == "1":
                        if not is_maintenance_bypass(request.url.path):
                            return JSONResponse(
                                status_code=503,
                                content={
                                    "success": False,
                                    "error": {
                                        "code": "MAINTENANCE_MODE",
                                        "message": "The system is currently undergoing maintenance and is in read-only mode.",
                                    },
                                },
                            )
            except Exception:
                # If Redis fails, fail open (let the request through)
                pass

        response = await call_next(request)
        return response
