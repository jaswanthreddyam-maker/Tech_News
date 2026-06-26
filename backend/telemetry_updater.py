import re

with open("app/api/v1/routes/telemetry.py", encoding="utf-8") as f:
    content = f.read()

# Add import for PipelineTelemetrySnapshot
if "PipelineTelemetrySnapshot" not in content:
    content = content.replace(
        "from app.schemas.responses import StandardResponse",
        "from app.schemas.responses import StandardResponse\nfrom app.schemas.monitoring import PipelineTelemetrySnapshot",
    )

# Replace get_telemetry_snapshot signature
# We will just write a new function body manually.

new_function = '''
async def get_telemetry_snapshot(db: AsyncSession) -> dict:
    """
    Computes a full real-time snapshot of the newsroom telemetry
    including source health counts, lifecycle status aggregates,
    queue depths from Redis, and trend spikes.
    """
    now_str = datetime.now(timezone.utc).isoformat()
    now_ts = datetime.now(timezone.utc)
    from datetime import timedelta
    time_limit_24h = now_ts - timedelta(hours=24)

    # 1. Current State
    queue_depth = 0
    active_crawls = 0
    active_workers = 0
    ai_queue_depth = 0
    try:
        redis_client = get_redis_client()
        queue_depth = await redis_client.llen("celery") or 0
        active_keys = await redis_client.keys("active_crawl:*")
        active_crawls = len(active_keys)

        ai_queue_raw = await redis_client.get("telemetry:v2:ai:queue")
        if ai_queue_raw:
            import json
            ai_queue_data = json.loads(ai_queue_raw)
            ai_queue_depth = ai_queue_data.get("depth", 0)

        # Count active workers based on heartbeat
        # Just a mock for now since exact active workers logic requires scanning redis keys
        worker_hb = await redis_client.get("telemetry:v2:heartbeat:tasks.monitoring.collect_infrastructure_metrics")
        active_workers = 1 if worker_hb else 0
    except Exception as e:
        logger.warning(f"Telemetry: Failed to fetch Redis current state: {e!s}")

    current_state = {
        "queue_depth": {"value": queue_depth, "source": "redis:celery", "updated_at": now_str, "window": "current"},
        "active_workers": {"value": active_workers, "source": "redis:heartbeat", "updated_at": now_str, "window": "current"},
        "active_crawlers": {"value": active_crawls, "source": "redis:active_crawl", "updated_at": now_str, "window": "current"},
        "ai_queue": {"value": ai_queue_depth, "source": "redis:telemetry_ai", "updated_at": now_str, "window": "current"}
    }

    # 2. Throughput
    ingestion_rate = 0.0
    try:
        time_limit_1m = now_ts - timedelta(minutes=1)
        rate_stmt = select(func.count(RawArticle.id)).where(RawArticle.scraped_at >= time_limit_1m)
        rate_res = await db.execute(rate_stmt)
        articles_past_minute = rate_res.scalar() or 0
        ingestion_rate = round(articles_past_minute / 60.0, 2)
    except Exception as e:
        logger.warning(f"Telemetry: Failed to compute throughput: {e!s}")

    throughput = {
        "ingestion_rate_sec": {"value": ingestion_rate, "source": "db:raw_articles", "updated_at": now_str, "window": "1m"}
    }

    # 3. Historical Counts
    all_time_counts = {
        "discovered": 0, "queued": 0, "fetched": 0, "filtered": 0,
        "deduplicated": 0, "processed": 0, "published": 0, "failed": 0
    }
    last_24h_counts = all_time_counts.copy()

    try:
        # All time Raw
        raw_stmt = select(RawArticle.status, func.count(RawArticle.id)).group_by(RawArticle.status)
        raw_res = await db.execute(raw_stmt)
        for status_str, count in raw_res.all():
            if status_str in all_time_counts:
                all_time_counts[status_str] = count

        # 24h Raw
        raw_stmt_24 = select(RawArticle.status, func.count(RawArticle.id)).where(RawArticle.scraped_at >= time_limit_24h).group_by(RawArticle.status)
        raw_res_24 = await db.execute(raw_stmt_24)
        for status_str, count in raw_res_24.all():
            if status_str in last_24h_counts:
                last_24h_counts[status_str] = count

        # All time Processed
        proc_stmt = select(ProcessedArticle.published_status, func.count(ProcessedArticle.id)).group_by(ProcessedArticle.published_status)
        proc_res = await db.execute(proc_stmt)
        all_processed = 0
        for status_str, count in proc_res.all():
            all_processed += count
            if status_str == "published":
                all_time_counts["published"] = count
        all_time_counts["processed"] = all_processed

        # 24h Processed
        proc_stmt_24 = select(ProcessedArticle.published_status, func.count(ProcessedArticle.id)).where(ProcessedArticle.created_at >= time_limit_24h).group_by(ProcessedArticle.published_status)
        proc_res_24 = await db.execute(proc_stmt_24)
        processed_24 = 0
        for status_str, count in proc_res_24.all():
            processed_24 += count
            if status_str == "published":
                last_24h_counts["published"] = count
        last_24h_counts["processed"] = processed_24

    except Exception as e:
        logger.warning(f"Telemetry: Failed to fetch historical stats: {e!s}")

    historical = {
        "all_time": all_time_counts,
        "last_24h": last_24h_counts
    }

    # 4. Quality
    thumbnail_coverage = 0.0
    avg_res = 0.0
    broken_images = 0
    fallback_usage = 0
    src_dist = {}

    try:
        total_stmt = select(func.count(ProcessedArticle.id))
        total_proc = (await db.execute(total_stmt)).scalar() or 0

        if total_proc > 0:
            dl_stmt = select(func.count(ProcessedArticle.id)).where(ProcessedArticle.thumbnail_local != None)
            dl_count = (await db.execute(dl_stmt)).scalar() or 0
            thumbnail_coverage = round((dl_count / total_proc) * 100.0, 2)

            fb_stmt = select(func.count(ProcessedArticle.id)).where(ProcessedArticle.thumbnail_source == "fallback")
            fallback_usage = (await db.execute(fb_stmt)).scalar() or 0

        # source distribution
        dist_stmt = select(ProcessedArticle.thumbnail_source, func.count(ProcessedArticle.id)).where(ProcessedArticle.thumbnail_source != None).group_by(ProcessedArticle.thumbnail_source)
        dist_res = await db.execute(dist_stmt)
        for src, count in dist_res.all():
            src_dist[src or "unknown"] = count
    except Exception as e:
        logger.warning(f"Telemetry: Failed to compute quality: {e!s}")

    # fetch ranking score
    ranking_enabled = False
    ranking_last_run = None
    avg_ranking_score = 0.0
    articles_evaluated = 0
    active_articles = 0
    expired_articles = 0

    try:
        redis_c = get_redis_client()
        rank_json = await redis_c.get("ranking_engine_metrics")
        if rank_json:
            import json
            rk = json.loads(rank_json)
            ranking_enabled = True
            ranking_last_run = rk.get("last_run")
            avg_ranking_score = rk.get("avg_final_score", 0.0)
            articles_evaluated = rk.get("articles_evaluated", 0)
            active_articles = rk.get("active_articles", 0)
            expired_articles = rk.get("expired_articles", 0)
    except Exception as e:
        logger.warning(f"Telemetry: Failed to fetch ranking metrics: {e!s}")

    quality = {
        "thumbnail_coverage": {"value": thumbnail_coverage, "source": "db:processed", "updated_at": now_str, "window": "all_time"},
        "average_resolution": {"value": avg_res, "source": "db:processed", "updated_at": now_str, "window": "all_time"},
        "broken_images": {"value": broken_images, "source": "db:processed", "updated_at": now_str, "window": "all_time"},
        "fallback_usage": {"value": fallback_usage, "source": "db:processed", "updated_at": now_str, "window": "all_time"},
        "thumbnail_source_distribution": {"value": src_dist, "source": "db:processed", "updated_at": now_str, "window": "all_time"},
        "average_ranking_score": {"value": avg_ranking_score, "source": "redis:ranking", "updated_at": now_str, "window": "current"}
    }

    ranking_engine = {
        "enabled": ranking_enabled,
        "last_run": ranking_last_run,
        "articles_evaluated": {"value": articles_evaluated, "source": "redis:ranking", "updated_at": now_str, "window": "current"},
        "active_articles": {"value": active_articles, "source": "redis:ranking", "updated_at": now_str, "window": "current"},
        "expired_articles": {"value": expired_articles, "source": "redis:ranking", "updated_at": now_str, "window": "current"}
    }

    # 5. AI Engine
    ai_enabled = False
    ai_provider = "unknown"
    ai_model = "unknown"
    ai_healthy = False
    ai_success_rate = 0.0
    ai_fallback_rate = 0.0
    ai_cost = 0.0
    ai_tokens = 0
    ai_lat = 0.0

    try:
        redis_c = get_redis_client()
        ai_p_raw = await redis_c.get("telemetry:v2:ai:provider")
        if ai_p_raw:
            import json
            ap = json.loads(ai_p_raw)
            ai_enabled = ap.get("enabled", False)
            ai_provider = ap.get("name", "unknown")
            ai_model = ap.get("model", "unknown")
            ai_healthy = ap.get("healthy", False)

        ai_perf_raw = await redis_c.get("telemetry:v2:ai:performance")
        if ai_perf_raw:
            import json
            apf = json.loads(ai_perf_raw)
            ai_success_rate = apf.get("success_rate", 0.0)
            ai_fallback_rate = apf.get("fallback_rate", 0.0)
            ai_lat = apf.get("latency", {}).get("p95", 0.0)

        ai_c_raw = await redis_c.get("telemetry:v2:ai:cost")
        if ai_c_raw:
            import json
            ac = json.loads(ai_c_raw)
            ai_cost = ac.get("usd", {}).get("today", 0.0)
            ai_tokens = ac.get("tokens", {}).get("total", 0)
    except Exception as e:
        logger.warning(f"Telemetry: Failed to fetch AI stats: {e!s}")

    ai_engine = {
        "enabled": ai_enabled,
        "provider_name": ai_provider,
        "provider_model": ai_model,
        "healthy": ai_healthy,
        "success_rate": {"value": ai_success_rate, "source": "redis:ai:perf", "updated_at": now_str, "window": "24h"},
        "fallback_rate": {"value": ai_fallback_rate, "source": "redis:ai:perf", "updated_at": now_str, "window": "24h"},
        "cost_usd_today": {"value": ai_cost, "source": "redis:ai:cost", "updated_at": now_str, "window": "today"},
        "tokens_total": {"value": ai_tokens, "source": "redis:ai:cost", "updated_at": now_str, "window": "today"},
        "average_latency_p95": {"value": ai_lat, "source": "redis:ai:perf", "updated_at": now_str, "window": "24h"}
    }

    # Build old lifecycle_states for backwards compat
    lifecycle_states = all_time_counts.copy()
    lifecycle_states["trend_scored"] = 0
    lifecycle_states["ai_queued"] = 0

    return {
        "current_state": current_state,
        "throughput": throughput,
        "quality": quality,
        "historical": historical,
        "ai_engine": ai_engine,
        "ranking_engine": ranking_engine,
        "lifecycle_states": lifecycle_states,
        "_meta": {"schema_version": 3}
    }
'''

# Use regex to replace the function definition completely
pattern = re.compile(
    r'async def get_telemetry_snapshot\(db: AsyncSession\) -> dict:.*?(?=@router\.get\("/status")', re.DOTALL
)
content = pattern.sub(new_function + "\n\n", content)

content = content.replace(
    '@router.get("", response_model=StandardResponse[dict])',
    '@router.get("", response_model=StandardResponse[PipelineTelemetrySnapshot])',
)

# Update SSE generator
sse_pattern = re.compile(r'(yield f"data: \{json\.dumps\(snapshot\)\}\\n\\n")')
new_sse = r"""snapshot_obj = PipelineTelemetrySnapshot(**snapshot)
                    yield f"data: {snapshot_obj.model_dump_json(by_alias=True)}\n\n\""""
content = sse_pattern.sub(new_sse, content)

with open("app/api/v1/routes/telemetry.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated telemetry.py")
