import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.schemas.monitoring import HealthSnapshot
from app.services.monitoring.evaluation import HealthEvaluationService

logger = logging.getLogger("tech_news.monitoring.checkers")


@runtime_checkable
class ServiceChecker(Protocol):
    """
    Protocol definition for health check probes.
    """

    service_name: str

    async def check(self) -> HealthSnapshot:
        """
        Executes a diagnostic probe on the target service and returns a typed HealthSnapshot.
        """
        ...


class PostgresChecker:
    service_name = "postgres"

    async def check(self) -> HealthSnapshot:
        t0 = time.perf_counter()
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
                latency_ms = (time.perf_counter() - t0) * 1000

                size_res = await db.execute(text("SELECT pg_database_size(current_database())"))
                size_bytes = size_res.scalar() or 0

                cache_res = await db.execute(
                    text("""
                    SELECT 
                        coalesce(sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read) + 1e-9), 1.0)
                    FROM pg_statio_user_tables
                """)
                )
                cache_hit_ratio = float(cache_res.scalar() or 1.0)

                longest_res = await db.execute(
                    text("""
                    SELECT coalesce(max(extract(epoch from (now() - query_start))), 0.0)
                    FROM pg_stat_activity
                    WHERE state = 'active'
                      AND query NOT LIKE '%%pg_stat_activity%%'
                      AND query NOT LIKE '%%SELECT 1%%'
                """)
                )
                longest_query_sec = float(longest_res.scalar() or 0.0)

            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=True,
                latency_ms=latency_ms,
                metrics={
                    "database_size_bytes": size_bytes,
                    "cache_hit_ratio": round(cache_hit_ratio, 4),
                    "longest_running_query_sec": round(longest_query_sec, 2),
                },
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.error(f"PostgresChecker failed: {e}", exc_info=True)
            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=False,
                latency_ms=latency_ms,
                metrics={},
                error=str(e),
                status_reason="connection_refused",
            )


class RedisChecker:
    service_name = "redis"

    async def check(self) -> HealthSnapshot:
        t0 = time.perf_counter()
        try:
            client = get_redis_client()
            pong = await asyncio.wait_for(client.ping(), timeout=3.0)
            latency_ms = (time.perf_counter() - t0) * 1000

            if not pong:
                raise ConnectionError("Redis ping did not return true response.")

            info = await client.info()
            clients = int(info.get("connected_clients", 0))
            used_mem = int(info.get("used_memory", 0))
            uptime = int(info.get("uptime_in_seconds", 0))
            frag_ratio = float(info.get("mem_fragmentation_ratio", 1.0))

            db0_info = info.get("db0", {})
            key_count = db0_info.get("keys", 0) if isinstance(db0_info, dict) else 0

            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=True,
                latency_ms=latency_ms,
                metrics={
                    "uptime_seconds": uptime,
                    "connected_clients": clients,
                    "used_memory_bytes": used_mem,
                    "key_count": key_count,
                    "fragmentation_ratio": round(frag_ratio, 2),
                },
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.error(f"RedisChecker failed: {e}", exc_info=True)
            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=False,
                latency_ms=latency_ms,
                metrics={},
                error=str(e),
                status_reason="redis_unreachable",
            )


class WorkerChecker:
    service_name = "worker"

    async def check(self) -> HealthSnapshot:
        t0 = time.perf_counter()
        try:
            from celery_app import celery_app

            def inspect_workers():
                inspector = celery_app.control.inspect()
                pings = inspector.ping()
                active = inspector.active()
                return pings, active

            pings, active = await asyncio.wait_for(asyncio.to_thread(inspect_workers), timeout=3.0)
            latency_ms = (time.perf_counter() - t0) * 1000

            workers_online = len(pings) if pings else 0
            active_count = sum(len(tasks) for tasks in active.values()) if active else 0

            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=True,
                latency_ms=latency_ms,
                metrics={
                    "workers_online": workers_online,
                    "active_tasks": active_count,
                    "workers": list(pings.keys()) if pings else [],
                },
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.warning(f"WorkerChecker query failed/timed out: {e}")
            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=False,
                latency_ms=latency_ms,
                metrics={"workers_online": 0, "active_tasks": 0},
                error=str(e),
                status_reason="timeout",
            )


class BeatChecker:
    service_name = "beat"

    async def check(self) -> HealthSnapshot:
        t0 = time.perf_counter()
        try:
            client = get_redis_client()
            heartbeat_val = await client.get("telemetry:v2:celery_beat_heartbeat")
            latency_ms = (time.perf_counter() - t0) * 1000

            if not heartbeat_val:
                return HealthEvaluationService.evaluate(
                    service_name=self.service_name,
                    available=False,
                    latency_ms=latency_ms,
                    metrics={},
                    error="No heartbeat timestamp registered in Redis.",
                    status_reason="heartbeat_expired",
                )

            val_str = heartbeat_val.decode("utf-8") if isinstance(heartbeat_val, bytes) else heartbeat_val
            try:
                import json

                payload = json.loads(val_str)
                beat_ts = payload.get("last_tick")
                metrics = {
                    "last_heartbeat": beat_ts,
                    "scheduler_version": payload.get("scheduler_version", "unknown"),
                    "hostname": payload.get("hostname", "unknown"),
                    "pid": payload.get("pid", 0),
                }
            except Exception:
                beat_ts = val_str
                metrics = {"last_heartbeat": beat_ts}

            dt = datetime.fromisoformat(beat_ts.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_s = (now - dt).total_seconds()

            metrics["heartbeat_age_seconds"] = round(age_s, 1)

            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=True,
                latency_ms=latency_ms,
                metrics=metrics,
                heartbeat_age_ms=age_s * 1000.0,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.error(f"BeatChecker failed: {e}", exc_info=True)
            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=False,
                latency_ms=latency_ms,
                metrics={},
                error=str(e),
                status_reason="redis_unreachable",
            )


class BackendChecker:
    service_name = "backend"

    async def check(self) -> HealthSnapshot:
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(settings.BACKEND_HEALTH_URL)
                latency_ms = (time.perf_counter() - t0) * 1000

                status_reason = None
                if res.status_code != 200:
                    status_reason = "http_error"

                return HealthEvaluationService.evaluate(
                    service_name=self.service_name,
                    available=True,
                    latency_ms=latency_ms,
                    metrics={"status_code": res.status_code},
                    error=f"Unhealthy status code: {res.status_code}" if res.status_code != 200 else None,
                    status_reason=status_reason,
                )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.warning(f"Backend HTTP check failed: {e}")
            return HealthEvaluationService.evaluate(
                service_name=self.service_name,
                available=False,
                latency_ms=latency_ms,
                metrics={},
                error=str(e),
                status_reason="timeout" if isinstance(e, httpx.TimeoutException) else "connection_refused",
            )
