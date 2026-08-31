import asyncio
import logging
import socket
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.models.article import ProcessedArticle, RawArticle
from app.models.growth import FeatureFlag
from app.models.source import Source
from app.models.user import AIJobHistory
from app.schemas.monitoring import HealthSnapshot, HealthStatus
from app.services.monitoring.checkers import (
    BackendChecker,
    BeatChecker,
    PostgresChecker,
    RedisChecker,
    WorkerChecker,
)
from app.services.monitoring.repository import MonitoringRepository

logger = logging.getLogger("tech_news.observability.service")


def calculate_health_grade(score: int) -> str:
    """
    Maps a numerical health score to a standard letter grade.
    """
    if score >= 98:
        return "A+"
    elif score >= 95:
        return "A"
    elif score >= 90:
        return "B"
    elif score >= 80:
        return "C"
    else:
        return "F"


async def run_infrastructure_health_checks(pipe=None):
    """
    Background worker execution controller. Runs all 6 core checkers concurrently
    using asyncio, updates rolling histories, and writes snapshots to Redis via the repo.
    """
    repo = MonitoringRepository()
    checkers = [PostgresChecker(), RedisChecker(), WorkerChecker(), BeatChecker(), BackendChecker()]

    logger.info("Observability: Running concurrent infrastructure health checks...")

    # 1. Execute check probes concurrently
    results = await asyncio.gather(*[c.check() for c in checkers], return_exceptions=True)

    snapshots: list[HealthSnapshot] = []

    from app.services.monitoring.evaluation import HealthEvaluationService

    # 2. Process results and handle exceptions gracefully
    for checker, result in zip(checkers, results):
        if isinstance(result, Exception):
            logger.error(f"Checker '{checker.service_name}' raised an unhandled error: {result}")
            snapshot = HealthEvaluationService.evaluate(
                service_name=checker.service_name,
                available=False,
                latency_ms=0.0,
                metrics={},
                error=f"Internal checker exception: {result!s}",
                status_reason="collector_error",
            )
        else:
            snapshot = result

        snapshots.append(snapshot)
        # Save atomically
        await repo.save_health_snapshot(snapshot, pipe=pipe)

    # 3. Calculate Overall Health Score
    # Load Queue Status to include in health scoring
    queue_status = HealthStatus.ONLINE
    queue_data = await repo.get_queue()
    if queue_data:
        queue_status = (
            HealthStatus.from_str(queue_data.get("status", "ONLINE"))
            if hasattr(HealthStatus, "from_str")
            else HealthStatus(queue_data.get("status", "ONLINE"))
        )

    # Define service status scores
    status_multipliers = {
        HealthStatus.ONLINE: 1.0,
        HealthStatus.DELAYED: 0.85,
        HealthStatus.DEGRADED: 0.5,
        HealthStatus.ERROR: 0.2,
        HealthStatus.OFFLINE: 0.0,
        HealthStatus.UNKNOWN: 0.0,
    }

    raw_weights = {"postgres": 30, "redis": 20, "worker": 15, "beat": 10, "queue": 10, "backend": 10}
    total_weight = sum(raw_weights.values())

    weighted_score = 0.0

    for snapshot in snapshots:
        weight = raw_weights.get(snapshot.service, 0)
        multiplier = status_multipliers.get(snapshot.status, 0.0)
        weighted_score += weight * multiplier

    # Add queue status weight
    queue_multiplier = status_multipliers.get(queue_status, 1.0)
    weighted_score += raw_weights["queue"] * queue_multiplier

    final_score = round((weighted_score / total_weight) * 100)
    final_grade = calculate_health_grade(final_score)

    # Cache the computed health score and status inside the infrastructure status
    score_payload = {
        "score": final_score,
        "grade": final_grade,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "_meta": {
            "schema_version": 2,
            "collector_version": "2.0",
            "build": "7.10",
            "git_sha": "rc1_certified",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=35)).isoformat(),
            "hostname": socket.gethostname(),
        },
    }

    client = get_redis_client()
    if pipe is not None:
        pipe.set("telemetry:v2:health_score", json_dumps_helpers(score_payload), ex=35)
    else:
        await client.set("telemetry:v2:health_score", json_dumps_helpers(score_payload), ex=35)

    logger.info(f"Observability Check Complete. Score: {final_score}/100 ({final_grade})")


async def run_queue_health_checks(pipe=None):
    """
    Queries Redis queues and execution logs to compute queue depth,
    growth rates, and processing rates in real time.
    """
    repo = MonitoringRepository()
    client = get_redis_client()
    now_str = datetime.now(timezone.utc).isoformat()

    try:
        _t = time.perf_counter  # alias for readability
        _timings = {}

        # 1-3. Batch all Redis reads into a single pipelined round trip
        _t0 = _t()
        now_ts = time.time()
        read_pipe = client.pipeline()
        read_pipe.llen("celery")
        read_pipe.zremrangebyscore("completed_tasks_timestamps", "-inf", now_ts - 60)
        read_pipe.zcard("completed_tasks_timestamps")
        read_pipe.get("last_queue_depth")
        p_res = await read_pipe.execute()
        _timings["redis_pipeline_read"] = (_t() - _t0) * 1000

        queue_depth = p_res[0] or 0
        processing_rate = p_res[2] or 0
        prev_depth_val = p_res[3]
        prev_depth = int(prev_depth_val) if prev_depth_val else 0
        growth_rate = queue_depth - prev_depth

        # 4. Status determination
        available = True
        status_reason = None
        error_msg = None

        # If queue has over 100 pending items and processing is stuck, mark degraded
        if queue_depth > 100 and processing_rate == 0:
            status_reason = "queue_stuck"
            error_msg = "Queue depth backlog accumulation with zero worker throughput."

        from app.services.monitoring.evaluation import HealthEvaluationService

        _t0 = _t()
        snapshot = HealthEvaluationService.evaluate(
            service_name="queue",
            available=available,
            latency_ms=0.0,
            metrics={
                "queue_depth": queue_depth,
                "processing_rate_jobs_min": processing_rate,
                "growth_rate_jobs_5s": growth_rate,
            },
            error=error_msg,
            status_reason=status_reason,
        )
        _timings["evaluate"] = (_t() - _t0) * 1000

        queue_payload = snapshot.model_dump()
        # For backwards compatibility with the raw dictionary saving
        queue_payload["status"] = (
            queue_payload["status"].value if hasattr(queue_payload["status"], "value") else queue_payload["status"]
        )

        _t0 = _t()
        if pipe is not None:
            pipe.set("last_queue_depth", str(queue_depth))
            await repo.save_queue(queue_payload, pipe=pipe)
        else:
            write_pipe = client.pipeline(transaction=True)
            write_pipe.set("last_queue_depth", str(queue_depth))
            await repo.save_queue(queue_payload, pipe=write_pipe)
            await write_pipe.execute()
        _timings["save_queue_and_depth"] = (_t() - _t0) * 1000

        _total = sum(_timings.values())
        if _total > 300:
            logger.warning(
                f"Queue collector profiling: total={_total:.1f}ms | "
                + " | ".join(f"{k}={v:.1f}ms" for k, v in _timings.items())
            )

        logger.info(
            f"Queue telemetry updated: depth={queue_depth}, processing_rate={processing_rate}, growth_rate={growth_rate}"
        )

    except Exception as e:
        logger.error(f"run_queue_health_checks failed: {e}", exc_info=True)
        from app.services.monitoring.evaluation import HealthEvaluationService

        snapshot = HealthEvaluationService.evaluate(
            service_name="queue",
            available=False,
            latency_ms=0.0,
            metrics={"queue_depth": 0, "processing_rate_jobs_min": 0, "growth_rate_jobs_5s": 0},
            error=str(e),
            status_reason="collector_error",
        )
        queue_payload = snapshot.model_dump()
        queue_payload["status"] = (
            queue_payload["status"].value if hasattr(queue_payload["status"], "value") else queue_payload["status"]
        )
        await repo.save_queue(queue_payload, pipe=pipe)


async def run_overview_health_checks(pipe=None):
    """
    Queries database counts for sources, articles, AI jobs, and general pipeline state.
    Calculates overall metrics at 60-second intervals.
    """
    repo = MonitoringRepository()
    now_str = datetime.now(timezone.utc).isoformat()

    data = {
        "generated_at": now_str,
        "source_health": {},
        "article_pipeline": {},
        "ai_queue": {},
        "emergency_cutoff_active": False,
    }

    try:
        async with AsyncSessionLocal() as db:
            # 1. Sources Health Stats
            sources_stmt = select(
                func.count(Source.id),
                func.sum(case((Source.enabled == True, 1), else_=0)),
                func.sum(case((Source.health_state == "healthy", 1), else_=0)),
                func.sum(case((Source.health_state == "degraded", 1), else_=0)),
                func.sum(case((Source.health_state == "failed", 1), else_=0)),
            )
            sources_res = await db.execute(sources_stmt)
            total_sources, enabled_sources, healthy_sources, degraded_sources, failed_sources = sources_res.first() or (
                0,
                0,
                0,
                0,
                0,
            )
            data["source_health"] = {
                "total": total_sources or 0,
                "enabled": enabled_sources or 0,
                "healthy": healthy_sources or 0,
                "degraded": degraded_sources or 0,
                "failed": failed_sources or 0,
            }

            # 2. Article Pipeline Stats
            articles_stmt = select(
                func.count(ProcessedArticle.id),
                func.sum(case((ProcessedArticle.published_status == "published", 1), else_=0)),
                func.sum(case((ProcessedArticle.published_status == "draft", 1), else_=0)),
            )
            articles_res = await db.execute(articles_stmt)
            total_processed, published_articles, draft_articles = articles_res.first() or (0, 0, 0)

            raw_stmt = select(func.count(RawArticle.id))
            raw_res = await db.execute(raw_stmt)
            total_raw = raw_res.scalar() or 0

            data["article_pipeline"] = {
                "raw": total_raw,
                "processed": total_processed or 0,
                "published": published_articles or 0,
                "draft": draft_articles or 0,
                "rejected": max(0, total_raw - (total_processed or 0)),
            }

            # 3. AI Jobs Stats
            ai_stmt = select(
                func.count(AIJobHistory.id),
                func.sum(case((AIJobHistory.status == "pending", 1), else_=0)),
                func.sum(case((AIJobHistory.status == "processing", 1), else_=0)),
                func.sum(case((AIJobHistory.status == "completed", 1), else_=0)),
                func.sum(case((AIJobHistory.status == "failed", 1), else_=0)),
            )
            ai_res = await db.execute(ai_stmt)
            total_jobs, queued_jobs, processing_jobs, completed_jobs, failed_jobs = ai_res.first() or (0, 0, 0, 0, 0)
            data["ai_queue"] = {
                "queued": queued_jobs or 0,
                "processing": processing_jobs or 0,
                "completed": completed_jobs or 0,
                "failed": failed_jobs or 0,
                "retry": 0,
            }

            # 4. Emergency Cutoff State
            flag_stmt = select(FeatureFlag).where(FeatureFlag.key == "emergency_pipeline_cutoff")
            flag_res = await db.execute(flag_stmt)
            cutoff_flag = flag_res.scalars().first()
            data["emergency_cutoff_active"] = cutoff_flag.default_value if cutoff_flag else False

        await repo.save_overview(data, pipe=pipe)
        logger.info("Dashboard overview metrics computed and cached successfully.")

    except Exception as e:
        logger.error(f"run_overview_health_checks failed: {e}", exc_info=True)
        # Save empty stats with error
        data["error"] = str(e)
        await repo.save_overview(data, pipe=pipe)


def json_dumps_helpers(obj: Any) -> str:
    import json

    return json.dumps(obj)


_feature_flag_cache: dict[str, tuple[bool, float]] = {}


async def collect_ai_queue_metrics(pipe=None):
    """Fast Collector (Every 10s): Queue and Provider Health"""
    try:
        from app.core.config import settings

        client = get_redis_client()
        now_utc = datetime.now(timezone.utc)
        _t = time.perf_counter  # alias for readability
        _timings = {}

        # Concurrently execute DB queries and batch-fetch Redis telemetry keys
        _t0 = _t()

        async def _fetch_db():
            async with AsyncSessionLocal() as db:
                from sqlalchemy import func

                queue_stats_res = await db.execute(
                    select(
                        func.count(RawArticle.id),
                        func.min(RawArticle.updated_at),
                        func.avg(RawArticle.retry_count),
                    ).where(RawArticle.status == "ai_queued")
                )

                # Check 60s in-memory cache for feature flag to eliminate unnecessary DB round-trips
                now_ts = time.time()
                cached_flag = _feature_flag_cache.get("ai_enrichment_enabled")
                if cached_flag is not None and now_ts < cached_flag[1]:
                    flag_enabled = cached_flag[0]
                else:
                    flag_res = await db.execute(select(FeatureFlag).where(FeatureFlag.key == "ai_enrichment_enabled"))
                    flag = flag_res.scalars().first()
                    flag_enabled = flag.default_value if flag else False
                    _feature_flag_cache["ai_enrichment_enabled"] = (flag_enabled, now_ts + 60.0)

                return queue_stats_res.one_or_none(), flag_enabled

        async def _fetch_redis():
            return await client.mget(
                "telemetry_failed_ai_jobs",
                "telemetry_recovered_ai_jobs",
                "telemetry_ai_last_success",
                "telemetry_ai_recent_errors",
            )

        db_results, redis_results = await asyncio.gather(_fetch_db(), _fetch_redis())
        _timings["concurrent_fetch"] = (_t() - _t0) * 1000

        queue_stats, enabled = db_results
        failed_raw, recovered_raw, last_success_ts, recent_errors_raw = redis_results

        depth = queue_stats[0] if queue_stats and queue_stats[0] else 0
        oldest = queue_stats[1] if queue_stats and queue_stats[1] else now_utc
        average_retry_count = float(queue_stats[2]) if queue_stats and queue_stats[2] else 0.0

        oldest_age_sec = (now_utc - oldest.replace(tzinfo=timezone.utc)).total_seconds() if oldest else 0
        estimated_average_wait_sec = oldest_age_sec / 2 if depth > 0 else 0  # Fast approximation for average wait

        failed_today = int(failed_raw or 0)
        recovered_today = int(recovered_raw or 0)

        queue_metrics = {
            "depth": depth,
            "oldest_age_sec": oldest_age_sec,
            "estimated_average_wait_sec": estimated_average_wait_sec,
            "average_retry_count": average_retry_count,
            "failed_today": failed_today,
            "recovered_today": recovered_today,
            "_meta": {
                "schema_version": 2,
                "collector_version": "2.0",
                "build": "7.10",
                "git_sha": "rc1_certified",
                "generated_at": now_utc.isoformat(),
                "expires_at": (now_utc + timedelta(seconds=15)).isoformat(),
                "hostname": socket.gethostname(),
            },
        }

        # Provider Metrics
        recent_errors = int(recent_errors_raw or 0)
        last_success_sec = (time.time() - float(last_success_ts)) if last_success_ts else 999999
        healthy = bool(enabled and (last_success_sec < 600) and (recent_errors < 50))

        provider_metrics = {
            "name": getattr(settings, "AI_PROVIDER", "openai"),
            "model": getattr(settings, "AI_MODEL", "gpt-4o-mini"),
            "enabled": enabled,
            "healthy": healthy,
            "last_success": datetime.fromtimestamp(float(last_success_ts), tz=timezone.utc).isoformat()
            if last_success_ts
            else None,
            "sdk_version": "v1.0.0",
            "_meta": {
                "schema_version": 2,
                "collector_version": "2.0",
                "build": "7.10",
                "git_sha": "rc1_certified",
                "generated_at": now_utc.isoformat(),
                "expires_at": (now_utc + timedelta(seconds=15)).isoformat(),
                "hostname": socket.gethostname(),
            },
        }

        # Batch write both payloads into a single Redis round trip
        _t0 = _t()
        if pipe is not None:
            pipe.set("telemetry:v2:ai:queue", json_dumps_helpers(queue_metrics), ex=30)
            pipe.set("telemetry:v2:ai:provider", json_dumps_helpers(provider_metrics), ex=30)
        else:
            write_pipe = client.pipeline(transaction=True)
            write_pipe.set("telemetry:v2:ai:queue", json_dumps_helpers(queue_metrics), ex=30)
            write_pipe.set("telemetry:v2:ai:provider", json_dumps_helpers(provider_metrics), ex=30)
            await write_pipe.execute()
        _timings["redis_pipeline_write"] = (_t() - _t0) * 1000

        _total = sum(_timings.values())
        if _total > 500:
            logger.warning(
                f"AI queue collector profiling: total={_total:.1f}ms | "
                + " | ".join(f"{k}={v:.1f}ms" for k, v in _timings.items())
            )

        logger.info("AI Fast Collector: Updated queue and provider telemetry.")
    except Exception as e:
        logger.error(f"collect_ai_queue_metrics failed: {e}", exc_info=True)


async def collect_ai_recovery_metrics(pipe=None):
    """Medium Collector (Every 30s): Recovery Metrics"""
    try:
        client = get_redis_client()
        recovered_raw, failed_raw = await client.mget("telemetry_recovered_ai_jobs", "telemetry_failed_ai_jobs")
        recovered_total = int(recovered_raw or 0)
        failed_total = int(failed_raw or 0)

        total = recovered_total + failed_total
        recovery_rate = recovered_total / total if total > 0 else 0.0

        recovery_metrics = {
            "recovered_total": recovered_total,
            "failed_total": failed_total,
            "recovery_rate": recovery_rate,
            "_meta": {
                "schema_version": 2,
                "collector_version": "2.0",
                "build": "7.10",
                "git_sha": "rc1_certified",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (now_utc + timedelta(seconds=45)).isoformat()
                if "now_utc" in locals()
                else (datetime.now(timezone.utc) + timedelta(seconds=45)).isoformat(),
                "hostname": socket.gethostname(),
            },
        }
        if pipe is not None:
            pipe.set("telemetry:v2:ai:recovery", json_dumps_helpers(recovery_metrics), ex=90)
        else:
            await client.set("telemetry:v2:ai:recovery", json_dumps_helpers(recovery_metrics), ex=90)
        logger.info("AI Medium Collector: Updated recovery telemetry.")
    except Exception as e:
        logger.error(f"collect_ai_recovery_metrics failed: {e}", exc_info=True)


async def collect_ai_performance_metrics(pipe=None):
    """Slow Collector (Every 60s): Performance and Cost Aggregates"""
    try:
        client = get_redis_client()
        async with AsyncSessionLocal() as db:
            # Query recent AIJobHistory (e.g. last 7 days)
            last_7d = datetime.now(timezone.utc) - timedelta(days=7)

            # 7 Days Cost
            stmt_7d = select(func.sum(AIJobHistory.cost_usd)).where(AIJobHistory.created_at >= last_7d)
            res_7d = await db.execute(stmt_7d)
            cost_7d = float(res_7d.scalar() or 0.0)

            # Yesterday Cost
            yesterday_start = datetime.now(timezone.utc) - timedelta(days=2)
            yesterday_end = datetime.now(timezone.utc) - timedelta(days=1)
            stmt_yest = select(func.sum(AIJobHistory.cost_usd)).where(
                AIJobHistory.created_at >= yesterday_start, AIJobHistory.created_at < yesterday_end
            )
            res_yest = await db.execute(stmt_yest)
            cost_yesterday = float(res_yest.scalar() or 0.0)

            # Today Metrics
            today = datetime.now(timezone.utc) - timedelta(days=1)
            stmt_today = select(
                func.count(AIJobHistory.id),
                func.sum(case((AIJobHistory.status == "completed", 1), else_=0)),
                func.sum(case((AIJobHistory.status == "failed", 1), else_=0)),
                func.sum(case((AIJobHistory.status == "fallback", 1), else_=0)),
                func.sum(case((AIJobHistory.cache_hit == True, 1), else_=0)),
                func.sum(AIJobHistory.prompt_tokens),
                func.sum(AIJobHistory.completion_tokens),
                func.sum(AIJobHistory.total_tokens),
                func.sum(AIJobHistory.cost_usd),
            ).where(AIJobHistory.created_at >= today)

            res_today = await db.execute(stmt_today)
            row = res_today.first()
            if row:
                (total_jobs, completed, failed, fallback, cache_hits, p_tokens, c_tokens, t_tokens, cost_today) = row
            else:
                total_jobs, completed, failed, fallback, cache_hits = 0, 0, 0, 0, 0
                p_tokens, c_tokens, t_tokens, cost_today = 0, 0, 0, 0.0

            completed = completed or 0
            failed = failed or 0
            fallback = fallback or 0
            total_jobs = total_jobs or 0
            cache_hits = cache_hits or 0
            cost_today = float(cost_today or 0.0)

            total_cf = completed + failed
            success_rate = completed / total_cf if total_cf > 0 else 0.0
            fallback_rate = fallback / total_jobs if total_jobs > 0 else 0.0
            failure_rate = failed / total_jobs if total_jobs > 0 else 0.0
            cache_hit_rate = cache_hits / total_jobs if total_jobs > 0 else 0.0
            avg_cost = cost_today / completed if completed > 0 else 0.0

            # Latency (over last 100 completed jobs)
            lat_stmt = (
                select(AIJobHistory.latency_ms)
                .where(AIJobHistory.status == "completed")
                .order_by(AIJobHistory.id.desc())
                .limit(100)
            )
            lat_res = await db.execute(lat_stmt)
            latencies = [l for l in lat_res.scalars().all() if l]

            if latencies:
                latencies.sort()
                p50 = latencies[int(len(latencies) * 0.50)]
                p95 = latencies[int(len(latencies) * 0.95)]
                max_lat = latencies[-1]
                avg_lat = sum(latencies) / len(latencies)
            else:
                p50, p95, max_lat, avg_lat = 0, 0, 0, 0

            now_utc = datetime.now(timezone.utc)
            performance_metrics = {
                "success_rate": success_rate,
                "fallback_rate": fallback_rate,
                "failure_rate": failure_rate,
                "latency": {"p50": p50, "p95": p95, "max": max_lat, "avg": avg_lat},
                "_meta": {
                    "schema_version": 2,
                    "collector_version": "2.0",
                    "build": "7.10",
                    "git_sha": "rc1_certified",
                    "generated_at": now_utc.isoformat(),
                    "expires_at": (now_utc + timedelta(seconds=90)).isoformat(),
                    "hostname": socket.gethostname(),
                },
            }

            cost_metrics = {
                "tokens": {"prompt": p_tokens or 0, "completion": c_tokens or 0, "total": t_tokens or 0},
                "usd": {"today": cost_today, "yesterday": cost_yesterday, "last_7d": cost_7d},
                "average_cost_per_article": avg_cost,
                "cache_hit_rate": cache_hit_rate,
                "_meta": {
                    "schema_version": 2,
                    "collector_version": "2.0",
                    "build": "7.10",
                    "git_sha": "rc1_certified",
                    "generated_at": now_utc.isoformat(),
                    "expires_at": (now_utc + timedelta(seconds=90)).isoformat(),
                    "hostname": socket.gethostname(),
                },
            }

            if pipe is not None:
                pipe.set("telemetry:v2:ai:performance", json_dumps_helpers(performance_metrics), ex=180)
                pipe.set("telemetry:v2:ai:cost", json_dumps_helpers(cost_metrics), ex=180)
            else:
                write_p = client.pipeline(transaction=True)
                write_p.set("telemetry:v2:ai:performance", json_dumps_helpers(performance_metrics), ex=180)
                write_p.set("telemetry:v2:ai:cost", json_dumps_helpers(cost_metrics), ex=180)
                await write_p.execute()

        logger.info("AI Slow Collector: Updated performance and cost telemetry.")
    except Exception as e:
        logger.error(f"collect_ai_performance_metrics failed: {e}", exc_info=True)
