import json
import socket
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.redis import get_redis_client
from app.schemas.monitoring import HealthSnapshot, HealthStatus, HistorySample


class MonitoringRepository:
    """
    Storage-agnostic repository encapsulating all observability caching,
    history tracking, and staleness validation logic in Redis.
    """

    async def get_health_snapshot(self, service_name: str) -> HealthSnapshot | None:
        """
        Retrieves the latest cached health snapshot for a service, applying strict
        staleness (freshness) validations to detect scheduler crashes.
        Handles Redis downtime gracefully.
        """
        try:
            client = get_redis_client()
            data = await client.get(f"telemetry:v2:health_snapshot:{service_name}")
            if not data:
                return None

            snapshot = HealthSnapshot.model_validate_json(data)

            # Freshness Check:
            # If cache is older than 2 * expected_interval, override status to UNKNOWN.
            try:
                last_checked_dt = datetime.fromisoformat(snapshot.last_checked.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                age = (now - last_checked_dt).total_seconds()

                # Determine interval bounds: Queue (5s), Overview (60s), others (10s)
                expected_interval = 5.0 if service_name == "queue" else 60.0 if service_name == "overview" else 10.0

                if age > 2 * expected_interval:
                    snapshot.status = HealthStatus.UNKNOWN
                    snapshot.error = (
                        f"Cache stale (last checked {round(age, 1)} seconds ago, expected <= {expected_interval}s)"
                    )
            except Exception as e:
                snapshot.status = HealthStatus.UNKNOWN
                snapshot.error = f"Freshness check failed to parse timestamp: {e!s}"

            return snapshot
        except Exception as e:
            # Handle Redis connection error
            now_str = datetime.now(timezone.utc).isoformat()
            if service_name == "redis":
                return HealthSnapshot(
                    service="redis",
                    status=HealthStatus.OFFLINE,
                    latency_ms=0.0,
                    last_checked=now_str,
                    error=f"Redis connection failed: {e!s}",
                )
            else:
                return HealthSnapshot(
                    service=service_name,
                    status=HealthStatus.UNKNOWN,
                    latency_ms=0.0,
                    last_checked=now_str,
                    error=f"Cache database offline: {e!s}",
                )

    async def save_health_snapshot(self, snapshot: HealthSnapshot, pipe=None):
        """
        Atomically updates the latest service snapshot, appends the rolling history log,
        and trims historical indicators using a single Redis transaction pipeline.
        """
        try:
            client = get_redis_client()

            # Look up previous state to preserve the last_success timestamp during failures
            prev = await self.get_health_snapshot(snapshot.service)
            if snapshot.status in (HealthStatus.ONLINE, HealthStatus.DEGRADED):
                snapshot.last_success = snapshot.last_checked
            elif prev:
                snapshot.last_success = prev.last_success

            history_item = HistorySample(
                timestamp=snapshot.last_checked, status=snapshot.status, latency_ms=snapshot.latency_ms
            )

            execute_pipe = False
            if pipe is None:
                pipe = client.pipeline(transaction=True)
                execute_pipe = True

            pipe.set(f"telemetry:v2:health_snapshot:{snapshot.service}", snapshot.model_dump_json(), ex=30)
            pipe.lpush(f"telemetry:v2:health_history:{snapshot.service}", history_item.model_dump_json())
            pipe.ltrim(f"telemetry:v2:health_history:{snapshot.service}", 0, 9)

            if execute_pipe:
                await pipe.execute()

        except Exception as e:
            print(f"MonitoringRepository: Failed to save snapshot for {snapshot.service}: {e}")

    async def get_history(self, service_name: str) -> list[HistorySample]:
        """
        Retrieves the rolling history of the last 10 status check samples.
        """
        try:
            client = get_redis_client()
            items = await client.lrange(f"telemetry:v2:health_history:{service_name}", 0, -1)
            samples = []
            for item in items:
                try:
                    val = item.decode("utf-8") if isinstance(item, bytes) else item
                    samples.append(HistorySample.model_validate_json(val))
                except Exception:
                    pass
            return samples
        except Exception:
            return []

    async def save_overview(self, overview_data: dict[str, Any], pipe=None):
        """
        Caches the high-level dashboard overview metadata.
        """
        try:
            client = get_redis_client()
            overview_data["_meta"] = {
                "schema_version": 2,
                "collector_version": "2.0",
                "build": "7.10",
                "git_sha": "rc1_certified",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=180)).isoformat(),
                "hostname": socket.gethostname(),
            }
            json_data = json.dumps(overview_data)
            if pipe is not None:
                pipe.set("telemetry:v2:overview", json_data, ex=180)
            else:
                await client.set("telemetry:v2:overview", json_data, ex=180)
        except Exception as e:
            print(f"MonitoringRepository: Failed to save overview: {e}")

    async def get_overview(self) -> dict[str, Any] | None:
        """
        Retrieves cached dashboard overview metadata, applying 2-minute freshness checks.
        """
        try:
            client = get_redis_client()
            data = await client.get("telemetry:v2:overview")
            if not data:
                return None

            parsed = json.loads(data)
            # Freshness check: overview generated_at should be <= 120 seconds old
            gen_time_str = parsed.get("generated_at")
            if gen_time_str:
                gen_dt = datetime.fromisoformat(gen_time_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if (now - gen_dt).total_seconds() > 120.0:
                    parsed["stale"] = True
            return parsed
        except Exception as e:
            # Return empty payload indicating cache is offline
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_health": {"total": 0, "healthy": 0, "degraded": 0, "failed": 0},
                "article_pipeline": {"raw": 0, "processed": 0, "published": 0, "draft": 0, "rejected": 0},
                "ai_queue": {"queued": 0, "processing": 0, "completed": 0, "failed": 0, "retry": 0},
                "emergency_cutoff_active": False,
                "error": f"Redis cache unavailable: {e!s}",
            }

    async def save_queue(self, queue_data: dict[str, Any], pipe=None):
        """
        Caches queue statistics.
        """
        try:
            client = get_redis_client()
            queue_data["_meta"] = {
                "schema_version": 2,
                "collector_version": "2.0",
                "build": "7.10",
                "git_sha": "rc1_certified",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
                "hostname": socket.gethostname(),
            }
            json_data = json.dumps(queue_data)
            if pipe is not None:
                pipe.set("telemetry:v2:queue", json_data, ex=30)
            else:
                await client.set("telemetry:v2:queue", json_data, ex=30)
        except Exception as e:
            print(f"MonitoringRepository: Failed to save queue metrics: {e}")

    async def get_queue(self) -> dict[str, Any] | None:
        """
        Retrieves cached queue statistics with a 10s freshness guard.
        """
        try:
            client = get_redis_client()
            data = await client.get("telemetry:v2:queue")
            if not data:
                return None

            parsed = json.loads(data)
            gen_time_str = parsed.get("generated_at")
            if gen_time_str:
                gen_dt = datetime.fromisoformat(gen_time_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if (now - gen_dt).total_seconds() > 10.0:
                    parsed["stale"] = True
            return parsed
        except Exception as e:
            return {
                "status": "OFFLINE",
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "error": f"Redis connection failed: {e!s}",
                "metrics": {"queue_depth": 0, "processing_rate_jobs_min": 0, "growth_rate_jobs_5s": 0},
            }

    async def save_metrics(self, metrics_data: dict[str, Any], pipe=None):
        """
        Caches general extensible metrics.
        """
        try:
            client = get_redis_client()
            metrics_data["_meta"] = {
                "schema_version": 2,
                "collector_version": "2.0",
                "build": "7.10",
                "git_sha": "rc1_certified",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
                "hostname": socket.gethostname(),
            }
            json_data = json.dumps(metrics_data)
            if pipe is not None:
                pipe.set("telemetry:v2:metrics", json_data, ex=300)
            else:
                await client.set("telemetry:v2:metrics", json_data, ex=300)
        except Exception as e:
            print(f"MonitoringRepository: Failed to save metrics: {e}")

    async def get_metrics(self) -> dict[str, Any] | None:
        """
        Retrieves general metrics.
        """
        try:
            client = get_redis_client()
            data = await client.get("telemetry:v2:metrics")
            if not data:
                return None
            return json.loads(data)
        except Exception:
            return None
