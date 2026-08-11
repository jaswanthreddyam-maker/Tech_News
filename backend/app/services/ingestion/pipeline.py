import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.ingestion.html_agent import HTMLAgent
from agents.ingestion.rss_agent import RSSIngestionAgent
from app.core.event_bus import publish_event
from app.models.article import ProcessedArticle, RawArticle
from app.models.source import Source
from app.services.ingestion.filter import (
    check_pre_ai_ingestion_eligibility,
    compute_title_similarity,
    evaluate_adaptive_quality,
)
from app.editorial.policy import PolicyLoader
from app.services.ingestion.acquisition_policy import ContentAcquisitionPolicy
from app.services.ingestion.persistence_service import PersistenceService
from app.services.ingestion.processor import (
    calculate_reading_time,
    clean_and_sanitize_html,
    decompress_html,
    generate_seo_metadata,
    generate_slug,
    map_category_id,
)
from app.services.ingestion.deduplication_service import DeduplicationService
from app.services.ingestion.extraction_service import ExtractionService
from app.services.ingestion.persistence_service import PersistenceService
from app.services.ingestion.rss_service import RSSService
from app.services.ingestion.utils import compress_content, get_hash, normalize_url, resolve_redirects

logger = logging.getLogger("tech_news.pipeline")

# Baseline configurations for rate limits
MAX_CONCURRENT_CRAWLS = 2
MIN_STAGGER_DELAY_SECONDS = 2.0
MAX_BACKOFF_INTERVAL_SECONDS = 86400  # 24 hours


async def run_source_ingestion_pipeline(db: AsyncSession) -> dict:
    """
    Core Ingestion Orchestrator (Hardened & Evolved).
    Loads active targets, enforces staggered intervals, performs URL canonicalization,
    fetches raw HTML with Boilerplate-free HTMLAgent cleaning, runs composite duplicate checks,
    separates zlib compressed content from JSON metadata, tracks states, and dynamically updates source credibility.
    """
    logger.info("Pipeline: Initializing real-time hardened ingestion cycle...")

    cycle_start_time = time.perf_counter()
    cycle_start_dt = datetime.now(timezone.utc)
    
    # 1. Fetch enabled crawling sources from the PostgreSQL SourceRegistry
    stmt = select(Source).where(Source.enabled == True)
    result = await db.execute(stmt)
    sources = result.scalars().all()
    await publish_event("PIPELINE", f"Ingestion cycle starting. {len(sources)} sources registered.", "info")

    metrics = {
        "sources_scanned": len(sources),
        "sources_crawled": 0,
        "sources_skipped_rate_limit": 0,
        "articles_discovered": 0,
        "articles_saved": 0,
        "duplicates_skipped": 0,
        "filtered_skipped": 0,
        "failed_crawls": 0,
        "degraded_fallback_count": 0,
        "html_refresh_attempts": 0,
        "html_refresh_success": 0,
        "html_refresh_permanent_failure": 0,
    }

    if not sources:
        logger.info("Pipeline: Zero active ingestion sources enabled in database.")
        return metrics

    rss_service = RSSService()
    extraction_service = ExtractionService()
    persistence_service = PersistenceService(db)
    dedup_service = DeduplicationService(db)
    
    policy = PolicyLoader.get_policy()
    allowed_rss_fallback_sources = set(policy.get("allow_rss_fallback", []))

    # Concurrency semaphore to prevent overloading downstream hosts
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CRAWLS)

    async def process_single_source(source: Source) -> None:
        persistence_service = PersistenceService(db)
        # Check source-specific rate policy
        current_time = datetime.now(timezone.utc)
        if source.last_crawl_at:
            elapsed = (current_time - source.last_crawl_at).total_seconds()
            if elapsed < source.crawl_interval:
                logger.info(
                    f"Pipeline: Skipping source '{source.name}' due to rate limits. "
                    f"Elapsed: {elapsed:.1f}s / Interval: {source.crawl_interval}s"
                )
                metrics["sources_skipped_rate_limit"] += 1
                return

        async with semaphore:
            logger.info(f"Pipeline: Orchestrating stream crawler for: {source.name} (Method: {source.method})")

            # Phase 2 Ingestion: Enforce RSS streams as high-value structured conduits
            if source.method != "rss":
                logger.info(
                    f"Pipeline: Skipping non-RSS source '{source.name}' (method: {source.method}) in Phase 2 Ingestion."
                )
                return

            metrics["sources_crawled"] += 1
            source.total_crawls += 1

            # Introduce stagger delay to prevent burst execution spikes across providers
            await asyncio.sleep(MIN_STAGGER_DELAY_SECONDS)

            t0 = time.time()
            try:
                # 1. Fetch items dynamically using RSSService
                crawled_items = await rss_service.fetch_feed_items_async(source.url)
                await publish_event(
                    f"RSS-{source.name.upper().replace(' ', '')[:12]}",
                    f"Fetched {len(crawled_items)} entries from {source.name}.",
                    "success",
                )

                # Check for parsing or network connection failures
                if not crawled_items:
                    raise RuntimeError("Crawl feed returned zero items or encountered network timeouts.")

                # Ingestion Rate Hardening: limit to top 10 latest articles to prevent thread/API congestion
                crawled_items = crawled_items[:10]

                # Update Source registry on success
                source.failure_count = 0
                source.health_state = "healthy"
                source.last_crawl_at = current_time
                source.successful_crawls += 1
                source.last_failure_type = None

                # Reset crawl interval to base config if it had been backed off
                source.crawl_interval = max(300, min(source.crawl_interval, 3600))

                # Recalculate historical reliability score
                source.reliability_score = round((source.successful_crawls / source.total_crawls) * 100.0, 2)

                # Collection of newly ingested/saved articles to process
                eligible_raw_articles = []

                # Parse source-specific parsing profile if defined in sources registry
                parser_profile = {}
                if source.parser_config:
                    try:
                        parser_profile = json.loads(source.parser_config)
                    except Exception as pe:
                        logger.warning(f"Pipeline: Failed to parse parser_config JSON for '{source.name}': {pe}")

                # 2. Process feed items
                for item in crawled_items:
                    metrics["articles_discovered"] += 1

                    raw_title = item["title"]
                    raw_url = item["url"]
                    rss_summary = item["summary"]

                    # A. Resilient URL Redirect Resolution
                    resolved_url = await resolve_redirects(raw_url)

                    # Normalization and Hashing (Duplicate-safe URL canonicalization)
                    normalized_url = normalize_url(resolved_url)
                    url_hash = get_hash(normalized_url)
                    title_hash = get_hash(raw_title)
                    existing_article = None

                    # B. Unified Deduplication Check via DeduplicationService
                    is_dup, reason, matched_id = await dedup_service.check_duplicate(raw_title, raw_url, current_time)

                    if is_dup:
                        metrics["duplicates_skipped"] += 1
                        await publish_event("DEDUPE-ENGINE", f"Rejected duplicate ({reason}): '{raw_title[:40]}'", "info")
                        await persistence_service.save_raw_article(
                            source_id=source.id,
                            title=raw_title,
                            url=normalized_url,
                            url_hash=url_hash,
                            title_hash=title_hash,
                            compressed_html=None,
                            clean_text=rss_summary,
                            metadata_dict={"reason": reason, "matched_article_id": matched_id},
                            status="deduplicated",
                            pipeline_version="1.0.0",
                            parser_version="1.0.0",
                        )
                        continue
                    elif reason == "retry_failed":
                        logger.info(f"Pipeline: Re-triggering failed/queued article crawl for: '{raw_title}' (ID: {matched_id})")
                        from sqlalchemy import select
                        res = await db.execute(select(RawArticle).where(RawArticle.id == matched_id))
                        existing_article = res.scalars().first()

                    # 3. Content Acquisition Policy v2 (Deterministic selection & provenance)
                    acquisition_policy = ContentAcquisitionPolicy(
                        rss_substantive_threshold=policy.get("rss_substantive_threshold", 100),
                        canonical_substantive_threshold=policy.get("canonical_substantive_threshold", 150)
                    )
                    source_policy_cfg = {
                        "allow_weak_rss_fallback": source.name in allowed_rss_fallback_sources,
                        "rss_substantive_threshold": getattr(source, "rss_substantive_threshold", 100),
                        "canonical_substantive_threshold": getattr(source, "canonical_substantive_threshold", 150),
                    }

                    rss_words = len((rss_summary or "").split())
                    html_duration = 0.0
                    extraction_res = None

                    if rss_words >= acquisition_policy.rss_substantive_threshold:
                        # Substantive RSS bypasses canonical HTTP fetch
                        acquisition_decision = acquisition_policy.evaluate(
                            rss_title=raw_title,
                            rss_text=rss_summary,
                            extraction_result=None,
                            source_policy=source_policy_cfg,
                        )
                        raw_html = item.get("raw_html") or rss_summary
                    else:
                        # Weak RSS triggers canonical extraction via ExtractionService
                        logger.info(f"Pipeline: RSS text non-substantive ({rss_words} words). Invoking ExtractionService for: {normalized_url}")
                        html_t0 = time.time()
                        extraction_res = await extraction_service.extract_content(
                            normalized_url, parser_config=parser_profile, source_name=source.name
                        )
                        html_duration = round((time.time() - html_t0) * 1000.0, 2)
                        raw_html = extraction_res.raw_html or item.get("raw_html") or rss_summary
                        acquisition_decision = acquisition_policy.evaluate(
                            rss_title=raw_title,
                            rss_text=rss_summary,
                            extraction_result=extraction_res,
                            source_policy=source_policy_cfg,
                        )

                    clean_body = acquisition_decision.selected_content
                    title_source = acquisition_decision.selected_title or raw_title
                    word_count = acquisition_decision.word_count
                    content_score = extraction_res.content_score if extraction_res and extraction_res.content_score > 0 else (50.0 if acquisition_decision.decision == "RSS_SELECTED" else 30.0)
                    density_score = extraction_res.density_score if extraction_res and extraction_res.density_score > 0 else 0.5
                    rss_fallback_used = acquisition_decision.decision == "RSS_FALLBACK_SELECTED"

                    # 4. Adaptive Content Quality Pipeline & Extraction Confidence Scoring
                    meta_dict = {
                        "source_category": source.category,
                        "source_name": source.name,
                        "rss_fallback": rss_fallback_used,
                        "allow_rss_fallback": source.name in allowed_rss_fallback_sources,
                        "author": item.get("author"),
                        "publish_date": item.get("publish_date"),
                        "seo_keywords": "",
                    }

                    quality_res = evaluate_adaptive_quality(
                        title=title_source, content=clean_body, raw_html=raw_html, meta_dict=meta_dict
                    )

                    if acquisition_decision.decision == "REJECTED":
                        is_eligible_quality = False
                        is_relevant = False
                        is_eligible = False
                        status_state = "filtered"
                        quality_res = {"eligible": False, "confidence": 0.0, "is_degraded": True, "reason": acquisition_decision.fallback_reason or "CANONICAL_EXTRACTION_REJECTED"}
                        logger.info(
                            f"Pipeline: Article '{raw_title[:50]}' REJECTED by ContentAcquisitionPolicy. Reason: {acquisition_decision.fallback_reason}"
                        )
                    else:
                        quality_res = evaluate_adaptive_quality(
                            title=title_source, content=clean_body, raw_html=raw_html, meta_dict=meta_dict
                        )
                        is_eligible_quality = quality_res["eligible"]
                        confidence_rating = quality_res.get("confidence", 0.0)

                        if quality_res.get("is_degraded", False):
                            is_relevant = True
                        else:
                            is_relevant = check_pre_ai_ingestion_eligibility(
                                title=title_source,
                                content=clean_body,
                                source_credibility=source.credibility_score,
                                source_category=source.category,
                            )
                        is_eligible = is_eligible_quality and is_relevant
                        status_state = "fetched" if is_eligible else "filtered"

                    # 5. Raw HTML Storage Strategy & Compression (zlib Level 9)
                    compressed_payload = compress_content(raw_html)

                    existing_meta = {}
                    if existing_article and existing_article.article_metadata:
                        try:
                            existing_meta = json.loads(existing_article.article_metadata)
                        except Exception:
                            pass

                    is_degraded = quality_res.get("is_degraded", False)
                    needs_html_refresh = is_degraded
                    html_retry_count = 0
                    next_retry_after = None
                    
                    html_refresh_policy = policy.get("html_refresh", {})
                    retry_schedule = html_refresh_policy.get("retry_schedule_hours", [1, 6, 24, 168])
                    max_attempts = html_refresh_policy.get("max_attempts", 4)

                    if existing_article and is_degraded:
                        metrics["html_refresh_attempts"] += 1
                        html_retry_count = existing_meta.get("html_retry_count", 0) + 1
                        
                        if html_retry_count <= max_attempts:
                            backoff_hours = retry_schedule[min(html_retry_count - 1, len(retry_schedule) - 1)]
                            next_retry_after = (current_time + timedelta(hours=backoff_hours)).isoformat()
                        else:
                            # Give up after max attempts
                            metrics["html_refresh_permanent_failure"] += 1
                            needs_html_refresh = False
                            
                    elif existing_article and not is_degraded:
                        # Successfully extracted HTML, clear retry fields
                        metrics["html_refresh_success"] += 1
                        needs_html_refresh = False
                        
                    if not existing_article and is_degraded:
                        metrics["degraded_fallback_count"] += 1

                    # Metadata Separation & Provenance Persistence (JSON serialized block)
                    meta_payload = {
                        "content_type": "text/html",
                        "response_time_ms": html_duration,
                        "content_score": content_score,
                        "density_score": density_score,
                        "word_count": word_count,
                        "extracted_at": current_time.isoformat(),
                        "parser": "ContentAcquisitionPolicy_v2",
                        "rss_fallback": rss_fallback_used,
                        "content_source": acquisition_decision.content_source,
                        "acquisition_decision": acquisition_decision.decision,
                        "rss_word_count": acquisition_decision.rss_word_count,
                        "canonical_word_count": acquisition_decision.canonical_word_count,
                        "canonical_extraction_status": acquisition_decision.canonical_extraction_status,
                        "fallback_reason": acquisition_decision.fallback_reason,
                        "content_revision": 1,
                        "extraction_confidence": quality_res.get("confidence", 0.0),
                        "quality_metrics": {
                            "paragraph_count": quality_res.get("paragraph_count", 0),
                            "unique_ratio": quality_res.get("unique_ratio", 0.0),
                            "markup_ratio": quality_res.get("markup_ratio", 0.0),
                            "reason": quality_res.get("reason", ""),
                            "is_degraded": is_degraded,
                        },
                        "quality_state": "DEGRADED" if is_degraded else "NORMAL",
                        "needs_html_refresh": needs_html_refresh,
                    }
                    
                    if is_degraded or (existing_article and "html_retry_count" in existing_meta):
                        meta_payload["html_retry_count"] = html_retry_count
                        if next_retry_after:
                            meta_payload["next_retry_after"] = next_retry_after
                        meta_payload["last_html_attempt"] = current_time.isoformat()

                    if existing_article:
                        content_changed = get_hash(existing_article.clean_text) != get_hash(clean_body)
                        
                        if content_changed:
                            # Update/Revision flow: update existing article fields and reset status
                            existing_article.title = title_source
                            existing_article.compressed_html = compressed_payload
                            existing_article.clean_text = clean_body
                            existing_article.article_metadata = json.dumps(meta_payload)
                            existing_article.parser_version = "1.0.0"
                            existing_article.status = status_state
                            existing_article.scraped_at = current_time
                            logger.info(f"Pipeline: Updated/revised existing article record for: '{title_source}'")
                        else:
                            # Content hash didn't change, just update metadata (e.g. retry counts)
                            existing_article.article_metadata = json.dumps(meta_payload)
                            existing_article.scraped_at = current_time
                            logger.info(f"Pipeline: Content hash unchanged for existing article '{title_source}', skipping re-enrichment.")
                    else:
                        # Insert new raw article via PersistenceService
                        new_article = await persistence_service.save_raw_article(
                            source_id=source.id,
                            title=title_source,
                            url=normalized_url,
                            url_hash=url_hash,
                            title_hash=title_hash,
                            compressed_html=compressed_payload,
                            clean_text=clean_body,
                            metadata_dict=meta_payload,
                            status=status_state,
                            pipeline_version="1.0.0",
                            parser_version="1.0.0",
                        )

                    if is_eligible:
                        metrics["articles_saved"] += 1
                        await publish_event(
                            "INGESTION", f"Stored article: '{title_source[:50]}' [{status_state}]", "success"
                        )
                        eligible_raw_articles.append(existing_article if existing_article else new_article)
                    else:
                        metrics["filtered_skipped"] += 1

                # Commit all article transactions for this source
                # (Notice: IMMEDIATE CELERY AI QUEUING HAS BEEN SUCCESSFULLY REMOVED. AI is now the last stage!)
                await db.commit()

            except Exception as e:
                import xml.etree.ElementTree as ET

                import httpx

                # Dynamic Failure Classification & Adaptive Backoff
                failure_type = "extraction_failed"
                error_msg = str(e)

                if isinstance(e, (asyncio.TimeoutError, httpx.TimeoutException, TimeoutError)):
                    failure_type = "timeout"
                elif isinstance(e, httpx.HTTPStatusError):
                    status_code = e.response.status_code
                    if status_code == 429:
                        failure_type = "rate_limited"
                        source.crawl_interval = min(MAX_BACKOFF_INTERVAL_SECONDS, source.crawl_interval * 4)
                    elif status_code == 403:
                        failure_type = "paywall_blocked"
                    elif status_code in (404, 410):
                        failure_type = "network_failure"
                        source.health_state = "offline"
                        source.enabled = False  # Auto-disable broken/defunct URLs
                    else:
                        failure_type = "network_failure"
                elif isinstance(
                    e, (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError, ConnectionError, OSError)
                ):
                    failure_type = "network_failure"
                elif (
                    isinstance(e, (ValueError, TypeError, json.JSONDecodeError, ET.ParseError))
                    or "xml" in error_msg.lower()
                    or "parser" in error_msg.lower()
                    or "feed" in error_msg.lower()
                ):
                    failure_type = "malformed_feed"
                elif "zero items" in error_msg.lower():
                    failure_type = "extraction_failed"

                source.failure_count += 1
                source.last_failure_type = failure_type
                if not source.enabled:
                    source.health_state = "offline"
                else:
                    source.health_state = (
                        "degraded"
                        if source.failure_count >= 3
                        else "offline"
                        if source.failure_count >= 5
                        else "healthy"
                    )

                # Evolve reliability & credibility
                source.reliability_score = round((source.successful_crawls / source.total_crawls) * 100.0, 2)
                penalty = 5 if failure_type in ("paywall_blocked", "rate_limited") else 2
                source.credibility_score = max(20, source.credibility_score - penalty * source.failure_count)

                # Standard exponential backoff (only if not already backed off aggressively)
                if failure_type != "rate_limited" and source.enabled:
                    source.crawl_interval = min(MAX_BACKOFF_INTERVAL_SECONDS, source.crawl_interval * 2)

                logger.error(
                    f"Pipeline: Ingestion failure classified as [{failure_type}] crawling source '{source.name}'. "
                    f"Failure count: {source.failure_count}. "
                    f"Applying backoff crawl interval: {source.crawl_interval}s. "
                    f"Error: {error_msg}",
                    exc_info=True,
                )
                metrics["failed_crawls"] += 1
                await publish_event(
                    f"RSS-{source.name.upper().replace(' ', '')[:12]}",
                    f"Crawl failed ({failure_type}): {error_msg[:80]}",
                    "warn",
                )
                await db.commit()

    # Process all sources
    for source in sources:
        try:
            await process_single_source(source)
        except Exception as e:
            logger.error(f"Pipeline: Critical exception processing source {source.name}: {e!s}", exc_info=True)
            metrics["failed_crawls"] += 1
            await db.rollback()


    logger.info(f"Pipeline: Hardened Ingestion complete. Metrics: {metrics}")

    # Save IngestionCycleMetrics
    cycle_duration = time.perf_counter() - cycle_start_time
    from app.models.ingestion import IngestionCycleMetrics
    
    cycle_metrics = IngestionCycleMetrics(
        started_at=cycle_start_dt,
        completed_at=datetime.now(timezone.utc),
        sources_scanned=metrics["sources_scanned"],
        sources_crawled=metrics["sources_crawled"],
        articles_discovered=metrics["articles_discovered"],
        articles_saved=metrics["articles_saved"],
        duplicates_skipped=metrics["duplicates_skipped"],
        filtered_skipped=metrics["filtered_skipped"],
        failed_crawls=metrics["failed_crawls"],
        duration_seconds=cycle_duration,
        status="completed" if metrics["failed_crawls"] == 0 else "completed_with_errors"
    )
    
    # Check for Depletion (active discovery but zero ingestion)
    if metrics["articles_discovered"] > 0 and metrics["articles_saved"] == 0:
        logger.warning(f"INGESTION_SAVE_FAILURE: Discovered {metrics['articles_discovered']} articles but saved 0! Relevance gates might be too strict.")
        await publish_event("PIPELINE-ALERT", "INGESTION_SAVE_FAILURE: Cycle yielded 0 articles despite active discovery.", "warn")
        cycle_metrics.status = "ingestion_save_failure"
        
    db.add(cycle_metrics)
    await db.commit()

    # Guardrail #2: State-change-aware batch cache invalidation ONLY if new articles were saved/published
    if metrics["articles_saved"] > 0:
        from app.services.cache_service import CacheService
        await CacheService.invalidate_homepage_cache(reason=f"ingestion_batch_saved_{metrics['articles_saved']}_articles")

    await publish_event(
        "PIPELINE",
        f"Ingestion complete. Saved={metrics['articles_saved']}, Dupes={metrics['duplicates_skipped']}, Failed={metrics['failed_crawls']}",
        "success",
    )
    return metrics


async def process_raw_article_to_editorial(db: AsyncSession, raw_id: int) -> dict:
    """
    Process raw article to clean, readable editorial format and save to processed_articles.
    Satisfies requirements: content sanitization, boilerplate removal, category mapping,
    reading time calculation, and SEO metadata generation.
    """
    logger.info(f"Processor: Executing content extraction for RawArticle ID: {raw_id}")

    # 1. Fetch raw article and join with source
    stmt = (
        select(RawArticle, Source).outerjoin(Source, RawArticle.source_id == Source.id).where(RawArticle.id == raw_id)
    )
    res = await db.execute(stmt)
    row = res.first()

    if not row:
        logger.error(f"Processor: RawArticle ID {raw_id} not found in database.")
        return {"status": "error", "message": "RawArticle not found."}

    raw_art, source_obj = row

    # 2. Extract raw html/text
    raw_html = ""
    if raw_art.compressed_html:
        raw_html = decompress_html(raw_art.compressed_html)

    if not raw_html:
        raw_html = raw_art.clean_text or ""

    # 3. Clean and sanitize HTML
    clean_html_content = clean_and_sanitize_html(raw_html)

    # Extract plain text content for word counts and summaries
    soup = BeautifulSoup(clean_html_content, "html.parser")
    plain_text = soup.get_text(separator=" ", strip=True)

    # Clean up whitespace
    plain_text = re.sub(r"\s+", " ", plain_text).strip()

    if not plain_text:
        plain_text = raw_art.clean_text or ""

    if not plain_text or len(plain_text.strip()) < 10:
        raw_art.status = "dead_letter"
        raw_art.dead_letter_reason = "Unparseable or empty text content"
        raw_art.dead_letter_at = datetime.now(timezone.utc)
        await db.commit()
        logger.warning(f"Processor: RawArticle ID {raw_id} marked as dead_letter due to empty text content.")
        return {"status": "dead_letter", "reason": "Empty text content"}

    # 5. Reading time
    reading_time = calculate_reading_time(plain_text)

    # 6. Slugification
    slug = generate_slug(raw_art.title)

    # 8. SEO Metadata
    seo_meta = generate_seo_metadata(raw_art.title, plain_text)

    # 9. Source attribution details
    source_name = source_obj.name if source_obj else "System Ingest"
    source_url = raw_art.url or (source_obj.url if source_obj else "")

    # 4. AI Pipeline Integration (Phase 4B)
    from app.ai.ai_pipeline import enrich_raw_article
    from app.ai.ai_repository import persist_telemetry
    from app.ai.config import AIConfig
    from app.ai.fingerprint import build_enrichment_input_fingerprint
    from app.ai.schemas import AIJobStatus, AITaskType
    from app.models.user import AIJobHistory

    ai_result = None
    already_enriched = False
    try:
        # Idempotency Check: prevent duplicate API calls if Celery retries
        existing_stmt = select(ProcessedArticle).where(ProcessedArticle.raw_article_id == raw_id)
        existing_res = await db.execute(existing_stmt)
        proc_art = existing_res.scalars().first()

        if proc_art and proc_art.ai_confidence == 99.0:
            ai_config = AIConfig()
            summary_prompt_version = ai_config.prompt_version_for(AITaskType.SUMMARY)
            ai_input_content = (raw_art.clean_text or "")[: ai_config.max_input_chars]
            current_fingerprint = build_enrichment_input_fingerprint(
                title=raw_art.title,
                content=ai_input_content,
                prompt_version=summary_prompt_version,
                provider=ai_config.provider,
                model=ai_config.model,
            )
            history_stmt = (
                select(AIJobHistory)
                .where(AIJobHistory.processed_article_id == proc_art.id)
                .where(AIJobHistory.enrichment_input_fingerprint == current_fingerprint)
                .where(AIJobHistory.status == AIJobStatus.COMPLETED)
            )
            history_res = await db.execute(history_stmt)
            if history_res.scalars().first():
                already_enriched = True

        if already_enriched:
            logger.info(f"Processor: Article {raw_id} already enriched with current config. Skipping AI.")
            summary = proc_art.summary
            tags_string = ",".join(proc_art.primary_topics) if getattr(proc_art, 'primary_topics', None) else ""
            seo_meta["seo_keywords"] = proc_art.seo_keywords
            sentiment = proc_art.sentiment
            confidence = proc_art.ai_confidence
        else:
            # Wrap the enrichment and persistence in a single logical transaction
            # db session already has an implicit transaction started by the initial select
            ai_result = await enrich_raw_article(db, raw_id)

            if ai_result and ai_result.status == AIJobStatus.COMPLETED:
                summary = ai_result.output.summary
                tags_string = ",".join(ai_result.output.tags)
                seo_meta["seo_keywords"] = ",".join(ai_result.output.keywords)
                sentiment = ai_result.output.sentiment.value if ai_result.output.sentiment else None
                confidence = getattr(ai_result.output, "category_confidence", 99.0)
                ai_category = getattr(ai_result.output, "primary_category", None)
                if ai_category:
                    ai_category = ai_category.value
            else:
                # Heuristic Fallback
                sentences = re.split(r"(?<=[.!?])\s+", plain_text)
                summary = " ".join(sentences[:2])
                if len(summary) > 280:
                    summary = summary[:277] + "..."
                if not summary:
                    summary = "No summary compiled yet."
                ai_category = None

                from app.services.ingestion.processor import extract_controlled_tags

                tags_string = extract_controlled_tags(raw_art.title, plain_text)
                sentiment = None

                # Resolve extraction confidence score from raw metadata
                confidence = 95.0
                if raw_art.article_metadata:
                    try:
                        meta = json.loads(raw_art.article_metadata)
                        confidence = float(meta.get("extraction_confidence", 95.0))
                    except Exception:
                        pass

    except Exception as e:
        logger.error(
            f"Processor: Unhandled exception during AI pipeline execution for RawArticle {raw_id}: {e}", exc_info=True
        )
        # Pipeline must never fail because AI failed.
        sentences = re.split(r"(?<=[.!?])\s+", plain_text)
        summary = " ".join(sentences[:2])
        if len(summary) > 280:
            summary = summary[:277] + "..."
        if not summary:
            summary = "No summary compiled yet."
        from app.services.ingestion.processor import extract_controlled_tags

        tags_string = extract_controlled_tags(raw_art.title, plain_text)
        sentiment = None
        confidence = 95.0
        ai_category = None

    # Fetch Category mapping
    from app.models.article import Category
    cat_res = await db.execute(select(Category.slug, Category.id, Category.name))
    cat_map = {row[0]: row[1] for row in cat_res.all()}

    # Resolve Category using AI or Fallback
    category_id = None
    if already_enriched and proc_art:
        category_id = proc_art.category_id
    elif ai_category and confidence >= 0.8:
        category_id = cat_map.get(ai_category)

    if not category_id:
        from app.services.ingestion.processor import map_category_id
        source_name = source_obj.name if source_obj else ""
        category_id = map_category_id(raw_art.title, plain_text, cat_map, source_name)

    # 12. Write or Update in processed_articles
    existing_stmt = select(ProcessedArticle).where(ProcessedArticle.raw_article_id == raw_id)
    existing_res = await db.execute(existing_stmt)
    proc_art = existing_res.scalars().first()

    # Resolve exact category name for the real-time event metadata payload
    try:
        cat_stmt = select(Category).where(Category.id == category_id)
        cat_res = await db.execute(cat_stmt)
        cat_obj = cat_res.scalars().first()
        category_name = cat_obj.name if cat_obj else "General"
    except Exception:
        category_name = "General"

    from app.services.ranking.news_ranking_engine import (
        calculate_engagement_score,
        calculate_final_score,
        calculate_freshness_score,
        calculate_impact_score,
        calculate_quality_score,
    )

    source_cred = source_obj.credibility_score if source_obj else 80

    if proc_art:
        # Update existing record
        proc_art.raw_article_id = raw_art.id
        proc_art.source_id = raw_art.source_id
        proc_art.category_id = category_id
        proc_art.title = raw_art.title
        proc_art.summary = summary
        proc_art.content = plain_text
        proc_art.source = source_name
        proc_art.source_name = source_name
        proc_art.source_url = source_url

        proc_art.primary_topics = [t.strip() for t in tags_string.split(",")] if tags_string else []
        proc_art.sentiment = sentiment
        proc_art.ai_confidence = confidence
        proc_art.reading_time = reading_time
        proc_art.seo_title = seo_meta["seo_title"]
        proc_art.seo_keywords = seo_meta["seo_keywords"]
        proc_art.readability_score = seo_meta["readability_score"]

        # Calculate updated scores
        from app.services.ranking.news_ranking_engine import get_lifecycle_policy
        _policy = get_lifecycle_policy()
        _default_ttl = int(_policy.get("maximum_ttl_hours", 72))
        impact = calculate_impact_score(raw_art.title, category_name, plain_text)
        freshness = calculate_freshness_score(proc_art.published_at)
        engagement = calculate_engagement_score(raw_art.article_metadata, source_cred)
        quality = calculate_quality_score(plain_text, raw_art.article_metadata)
        final = calculate_final_score(impact, freshness, engagement, quality)

        proc_art.freshness_score = freshness
        proc_art.engagement_score = engagement
        proc_art.final_score = final
        proc_art.expires_at = proc_art.published_at + timedelta(hours=_default_ttl)
        logger.info(f"Processor: Updated existing processed article record for slug: {slug}")
    else:
        # Create new processed record
        pub_at = datetime.now(timezone.utc)
        impact = calculate_impact_score(raw_art.title, category_name, plain_text)
        freshness = calculate_freshness_score(pub_at)
        engagement = calculate_engagement_score(raw_art.article_metadata, source_cred)
        quality = calculate_quality_score(plain_text, raw_art.article_metadata)
        final = calculate_final_score(impact, freshness, engagement, quality)

        proc_art = ProcessedArticle(
            raw_article_id=raw_art.id,
            source_id=raw_art.source_id,
            category_id=category_id,
            title=raw_art.title,
            slug=slug,
            summary=summary,
            content=clean_html_content,
            source=source_name,
            source_name=source_name,
            source_url=source_url,
            sentiment=sentiment,
            ai_confidence=confidence,
            reading_time=reading_time,
            seo_title=seo_meta["seo_title"],
            seo_keywords=seo_meta["seo_keywords"],
            readability_score=seo_meta["readability_score"],
            published_status="published",
            published_at=pub_at,
            expires_at=pub_at + timedelta(hours=_default_ttl),
            freshness_score=freshness,
            engagement_score=engagement,
            final_score=final,
        )
        persistence_service = PersistenceService(db)
        await persistence_service.save_processed_article(proc_art)
        logger.info(f"Processor: Inserted new processed article record with slug: {slug}")

    # 13. Persist Telemetry (if AI was attempted and not skipped via idempotency)
    if ai_result and ai_result.telemetry and not already_enriched:
        try:
            job_ids = await persist_telemetry(db, raw_art.id, proc_art.id, ai_result.telemetry)
            logger.info(f"Processor: Persisted {len(job_ids)} AI telemetry records for RawArticle {raw_art.id}")
        except Exception as e:
            logger.error(f"Processor: Failed to persist telemetry, rolling back transaction: {e}")
            await db.rollback()
            return {"status": "error", "message": "Failed to persist telemetry."}

    # 14. Background Thumbnail Download
    from app.services.ingestion.image_helper import extract_all_candidate_urls

    candidates = []
    if not getattr(proc_art, "thumbnail_url", None):
        candidates = extract_all_candidate_urls(raw_html, raw_art.url)
        # Flush session to assign ID to new proc_art before Celery tasks
        await db.flush()

    try:
        from app.tasks.article_intelligence import run_article_intelligence_pipeline
        from celery_app import download_thumbnail_task

        proc_art.embedding_status = "queued"
        run_article_intelligence_pipeline.delay(proc_art.id)
        logger.info(f"Processor: Enqueued Article Intelligence Pipeline for ProcessedArticle ID {proc_art.id}")

        if not getattr(proc_art, "thumbnail_url", None):
            from app.core.config import settings
            download_thumbnail_task.delay(proc_art.id, candidates[:settings.MAX_THUMBNAIL_CANDIDATES] if candidates else [])
            logger.info(f"Processor: Enqueued background thumbnail download for ProcessedArticle ID {proc_art.id}")
    except Exception as celery_err:
        logger.warning(f"Processor: Celery task enqueueing skipped (Redis/Broker offline): {celery_err}")

    # Mark raw article as processed
    raw_art.status = "processed"
    raw_art.processed_at = datetime.now(timezone.utc)

    # Emit ArticlePublished event for CQRS read model projection
    import hashlib

    from app.core.events.models import EventOutbox
    from app.core.events.schemas import ArticlePublishedPayload

    content_hash = hashlib.sha256(proc_art.content.encode('utf-8')).hexdigest() if proc_art.content else ""
    
    payload_model = ArticlePublishedPayload(
        id=str(proc_art.id),
        url=proc_art.slug,
        title=proc_art.title,
        content=proc_art.content,
        summary=proc_art.summary,
        hash=content_hash,
        source=proc_art.source_name,
        thumbnail_url=getattr(proc_art, "thumbnail_url", None),
        thumbnail_local=getattr(proc_art, "thumbnail_local", None),
        published_at=proc_art.published_at,
        is_test_data=getattr(proc_art, "is_test_data", False),
        key_takeaways=proc_art.key_takeaways,
        impact_score=float(proc_art.final_score) if proc_art.final_score else 0.0,
        freshness_score=float(proc_art.freshness_score) if proc_art.freshness_score else 0.0,
        engagement_score=float(proc_art.engagement_score) if proc_art.engagement_score else 0.0,
        final_score=float(proc_art.final_score) if proc_art.final_score else 0.0,
        reading_time=proc_art.reading_time if proc_art.reading_time else 0,
        tags=",".join(proc_art.primary_topics) if getattr(proc_art, 'primary_topics', None) else "",
        category=category_name,
        published_status=proc_art.published_status
    )

    outbox_event = EventOutbox(
        event_type="ArticlePublished",
        payload=payload_model.model_dump(mode="json")
    )
    db.add(outbox_event)

    # Invariant: Score must exist before projection to read model
    assert proc_art.final_score is not None and float(proc_art.final_score) > 0.0, \
        f"Cannot project article {proc_art.id} to ReadModel without a valid final_score"

    # Directly project to ArticleReadModel for instantaneous query availability
    from app.models.article import ArticleReadModel
    read_stmt = select(ArticleReadModel).where(ArticleReadModel.id == str(proc_art.id))
    read_res = await db.execute(read_stmt)
    existing_read = read_res.scalars().first()

    tags_list = proc_art.primary_topics or []

    incoming_revision = getattr(proc_art, "content_revision", 1) or 1
    existing_meta = {}
    if existing_read and getattr(existing_read, "article_metadata", None):
        try:
            existing_meta = json.loads(existing_read.article_metadata) if isinstance(existing_read.article_metadata, str) else (existing_read.article_metadata or {})
        except Exception:
            pass

    existing_revision = existing_meta.get("content_revision", 1)

    if existing_read and incoming_revision < existing_revision:
        logger.info(f"Pipeline: Skipping stale projection update for article ID {proc_art.id} (incoming_rev={incoming_revision} <= existing_rev={existing_revision})")
        return proc_art

    if existing_read:
        existing_read.title = proc_art.title
        existing_read.summary = proc_art.summary
        existing_read.content = proc_art.content
        existing_read.source = proc_art.source_name
        existing_read.published_at = proc_art.published_at
        existing_read.category = category_name
        existing_read.freshness_score = float(proc_art.freshness_score) if proc_art.freshness_score else 0.0
        existing_read.final_score = float(proc_art.final_score) if proc_art.final_score else 0.0
    else:
        new_read = ArticleReadModel(
            id=str(proc_art.id),
            url=proc_art.slug,
            title=proc_art.title,
            summary=proc_art.summary,
            content=proc_art.content,
            source=proc_art.source_name,
            hash=content_hash,
            editorial_status="DRAFT",
            publication_status="PUBLISHED",
            published_status=proc_art.published_status,
            published_at=proc_art.published_at,
            reading_time=proc_art.reading_time or 1,
            tags=tags_list,
            category=category_name,
            freshness_score=float(proc_art.freshness_score) if proc_art.freshness_score else 0.0,
            engagement_score=float(proc_art.engagement_score) if proc_art.engagement_score else 0.0,
            final_score=float(proc_art.final_score) if proc_art.final_score else 0.0,
        )
        db.add(new_read)

    await db.commit()

    try:
        from app.core.redis import get_redis_client
        redis = get_redis_client()
        await redis.delete("editorial:v1:homepage_ranked_ids")
        logger.info("Invalidated homepage ranked IDs cache due to new article publication.")
    except Exception as redis_err:
        logger.error(f"Failed to invalidate ranking cache on publication: {redis_err}")

    # Publish real-time event to Redis pub/sub channel for SSE clients
    await publish_event(
        "INGESTION",
        f"New article published: {proc_art.title}",
        "success",
        {
            "id": proc_art.id,
            "title": proc_art.title,
            "slug": proc_art.slug,
            "summary": proc_art.summary,
            "source": proc_art.source,
            "category": category_name,
            "published_at": proc_art.published_at.isoformat(),
        },
    )

    return {"status": "success", "processed_article_slug": slug}


async def crawl_single_source_pipeline(db: AsyncSession, source_id: int) -> dict:
    """
    Manually trigger an immediate, non-blocking crawling run for a specific source ID.
    Bypasses the `crawl_interval` rate limit to enforce operational control.
    """
    logger.info(f"Pipeline: Administrative force-crawl triggered for source ID: {source_id}")
    stmt = select(Source).where(Source.id == source_id)
    res = await db.execute(stmt)
    source = res.scalars().first()

    if not source:
        return {"status": "error", "message": f"Source ID {source_id} not found."}

    if not source.enabled:
        return {"status": "error", "message": f"Source '{source.name}' is currently disabled."}

    rss_service = RSSService()
    extraction_service = ExtractionService()
    persistence_service = PersistenceService(db)
    dedup_service = DeduplicationService(db)

    metrics = {
        "articles_discovered": 0,
        "articles_saved": 0,
        "duplicates_skipped": 0,
        "filtered_skipped": 0,
        "status": "success",
    }

    try:
        current_time = datetime.now(timezone.utc)
        source.total_crawls += 1

        # 1. Fetch items dynamically using RSSService
        crawled_items = await rss_service.fetch_feed_items_async(source.url)
        await publish_event("RSS-FORCE", f"Force crawled {len(crawled_items)} entries from {source.name}.", "success")

        if not crawled_items:
            raise RuntimeError("Crawl feed returned zero items.")

        crawled_items = crawled_items[:10]

        source.failure_count = 0
        source.health_state = "healthy"
        source.last_crawl_at = current_time
        source.successful_crawls += 1
        source.reliability_score = round((source.successful_crawls / source.total_crawls) * 100.0, 2)

        # Parse source-specific parsing profile if defined
        parser_profile = {}
        if source.parser_config:
            try:
                parser_profile = json.loads(source.parser_config)
            except Exception as pe:
                logger.warning(f"Pipeline: Failed to parse parser_config JSON for '{source.name}': {pe}")

        # 2. Process crawled items
        for item in crawled_items:
            metrics["articles_discovered"] += 1
            raw_title = item["title"]
            raw_url = item["url"]
            rss_summary = item["summary"]

            resolved_url = await resolve_redirects(raw_url)
            normalized_url = normalize_url(resolved_url)
            url_hash = get_hash(normalized_url)
            title_hash = get_hash(raw_title)

            # Deduplication via DeduplicationService
            is_dup, reason, matched_id = await dedup_service.check_duplicate(raw_title, raw_url, current_time)

            if is_dup:
                metrics["duplicates_skipped"] += 1
                await persistence_service.save_raw_article(
                    source_id=source.id,
                    title=raw_title,
                    url=normalized_url,
                    url_hash=url_hash,
                    title_hash=title_hash,
                    compressed_html=None,
                    clean_text=rss_summary,
                    metadata_dict={"reason": reason, "matched_article_id": matched_id},
                    status="deduplicated",
                )
                continue

            # Content extraction via ExtractionService
            html_t0 = time.time()
            has_content, extracted = await extraction_service.extract_content(
                normalized_url, parser_config=parser_profile, source_name=source.name
            )
            html_duration = round((time.time() - html_t0) * 1000.0, 2)

            raw_html = (
                extracted.get("raw_html")
                or item.get("raw_html")
                or ""
            )

            if has_content:
                clean_body = extracted["clean_text"]
                title_source = extracted.get("title") or raw_title
            else:
                clean_body = rss_summary
                title_source = raw_title

            if not raw_html:
                raw_html = rss_summary

            # Quality and relevance filtering
            meta_dict = {
                "source_category": source.category,
                "rss_fallback": not has_content,
                "author": item.get("author"),
                "publish_date": item.get("publish_date"),
            }
            quality_res = evaluate_adaptive_quality(
                title=title_source, content=clean_body, raw_html=raw_html, meta_dict=meta_dict
            )
            is_relevant, relevance_reason = check_pre_ai_ingestion_eligibility(
                title=title_source, content=clean_body, source_credibility=source.credibility_score, source_category=source.category
            )

            is_eligible = quality_res["eligible"] and is_relevant
            status_state = "fetched" if is_eligible else "filtered"

            filter_reason = None
            if not is_eligible:
                if not quality_res["eligible"]:
                    if quality_res.get("reason", "").startswith("Insufficient content length"):
                        filter_reason = "RSS_CONTENT_TOO_SHORT"
                    elif quality_res.get("reason", "").startswith("Truncated"):
                        filter_reason = "CANONICAL_EXTRACTION_EMPTY"
                    else:
                        filter_reason = "LOW_INFORMATION_DENSITY"
                else:
                    filter_reason = relevance_reason

            compressed_payload = compress_content(raw_html)
            meta_payload = {
                "content_type": "text/html",
                "response_time_ms": html_duration,
                "quality_metrics": {
                    "paragraph_count": quality_res.get("paragraph_count", 0),
                    "unique_ratio": quality_res.get("unique_ratio", 0.0),
                    "markup_ratio": quality_res.get("markup_ratio", 0.0),
                    "reason": quality_res.get("reason", ""),
                },
            }

            await persistence_service.save_raw_article(
                source_id=source.id,
                title=title_source,
                url=normalized_url,
                url_hash=url_hash,
                title_hash=title_hash,
                compressed_html=compressed_payload,
                clean_text=clean_body,
                metadata_dict=meta_payload,
                status=status_state,
                filter_reason=filter_reason
            )

            if is_eligible:
                metrics["articles_saved"] += 1
            else:
                metrics["filtered_skipped"] += 1

        await db.commit()
        await publish_event(
            "INGESTION", f"Force crawl complete. Source '{source.name}' successfully parsed.", "success"
        )

    except Exception as e:
        logger.error(f"Pipeline: Force crawl failed for source {source.name}: {e}", exc_info=True)
        await db.rollback()
        metrics["status"] = "error"
        metrics["message"] = str(e)

    return metrics
