from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.schemas.monitoring import HealthSnapshot, HealthStatus


class HealthEvaluationService:
    @staticmethod
    def evaluate(
        service_name: str,
        available: bool,
        latency_ms: float,
        metrics: dict[str, Any],
        error: str | None = None,
        status_reason: str | None = None,
        heartbeat_age_ms: float | None = None,
        ttl_remaining: float | None = None,
    ) -> HealthSnapshot:
        now_str = datetime.now(timezone.utc).isoformat()

        # Base failure mode: Collector error or unhandled exception
        if not available and status_reason == "collector_error":
            return HealthSnapshot(
                service=service_name,
                status=HealthStatus.UNKNOWN,
                available=False,
                status_reason=status_reason,
                latency_ms=round(latency_ms, 2),
                last_checked=now_str,
                metrics=metrics,
                error=error,
                collector_version=2,
                heartbeat_age_ms=heartbeat_age_ms,
                ttl_remaining=ttl_remaining,
            )

        # Get thresholds for the service
        thresholds = settings.HEALTH_THRESHOLDS.get(service_name, {})

        status = HealthStatus.ONLINE

        if not available:
            status = HealthStatus.OFFLINE
        else:
            # Service-specific logic
            if service_name == "beat" and heartbeat_age_ms is not None:
                age_s = heartbeat_age_ms / 1000.0
                if age_s >= thresholds.get("degraded", 45.0):
                    status = HealthStatus.OFFLINE
                    available = False
                    if not status_reason:
                        status_reason = "heartbeat_expired"
                    if not error:
                        error = f"Scheduler inactive: {age_s:.1f}s."
                elif age_s >= thresholds.get("delayed", 30.0):
                    status = HealthStatus.DEGRADED
                    if not error:
                        error = f"heartbeat delayed: {age_s:.1f}s."
                elif age_s >= thresholds.get("online", 10.0):
                    status = HealthStatus.DELAYED
                    if not error:
                        error = f"heartbeat delayed: {age_s:.1f}s."

            elif service_name in ["postgres", "redis", "backend"]:
                # If there's an error string or status_reason provided but it's "available" (e.g. 500 status code)
                if status_reason in ["http_500", "http_error", "unhealthy_status_code"]:
                    status = HealthStatus.ERROR
                elif latency_ms >= thresholds.get("degraded", 1000.0):
                    status = HealthStatus.DEGRADED
                    if not error:
                        error = f"High latency: {latency_ms:.1f}ms >= threshold."
                elif latency_ms >= thresholds.get("delayed", 300.0):
                    status = HealthStatus.DELAYED
                    if not error:
                        error = f"High latency: {latency_ms:.1f}ms >= threshold."

            elif service_name == "worker":
                workers_online = metrics.get("workers_online", 0)
                if workers_online == 0:
                    status = HealthStatus.OFFLINE
                    available = False
                    if not status_reason:
                        status_reason = "no_workers"
                    if not error:
                        error = "No active Celery workers."

        # Determine last success
        last_success = now_str if status in [HealthStatus.ONLINE, HealthStatus.DELAYED, HealthStatus.DEGRADED] else None

        return HealthSnapshot(
            service=service_name,
            status=status,
            available=available,
            status_reason=status_reason,
            latency_ms=round(latency_ms, 2),
            last_checked=now_str,
            last_success=last_success,
            metrics=metrics,
            error=error,
            collector_version=2,
            heartbeat_age_ms=heartbeat_age_ms,
            ttl_remaining=ttl_remaining,
        )
