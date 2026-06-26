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
from app.services.ingestion.processor import (
    calculate_reading_time,
    clean_and_sanitize_html,
    decompress_html,
    generate_seo_metadata,
    generate_slug,
    map_category_id,
)
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
    }

    if not sources:
        logger.info("Pipeline: Zero active ingestion sources enabled in database.")
        return metrics

    rss_agent = RSSIngestionAgent()
    html_agent = HTMLAgent()

    # Concurrency semaphore to prevent overloading downstream hosts
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CRAWLS)

    async def process_single_source(source: Source) -> None:
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
                # 1. Fetch items dynamically using RSS Agent
                crawled_items = await rss_agent.crawl_feed(source.url)
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
                # (For instance, if base was 900s, let's keep it at base or default to 900)
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

                    # B. Hard Deduplication check: check unique composite constraint (url_hash, title_hash) (Cheapest check)
                    dup_stmt = select(RawArticle).where(
                        (RawArticle.url_hash == url_hash) & (RawArticle.title_hash == title_hash)
                    )
                    dup_res = await db.execute(dup_stmt)
                    existing_article = dup_res.scalars().first()

                    if existing_article:
                        if existing_article.status in ("failed", "discovered"):
                            logger.info(f"Pipeline: Re-triggering failed/queued article crawl for: '{raw_title}'")
                        else:
                            logger.info(f"Pipeline: Skipping duplicate URL + Title pair for article: '{raw_title}'")
                            metrics["duplicates_skipped"] += 1
                            await publish_event("DEDUPE-ENGINE", f"Rejected duplicate: '{raw_title[:50]}'", "info")
                            continue

                    # C. Soft Deduplication: Multi-Signal Title Overlap (Past 24h)
                    # Compare only against unique unique articles to prevent comparison chain bloat
                    yesterday = current_time - timedelta(days=1)
                    soft_stmt = select(RawArticle).where(
                        (RawArticle.scraped_at >= yesterday) & (RawArticle.status != "deduplicated")
                    )
                    soft_res = await db.execute(soft_stmt)
                    recent_articles = soft_res.scalars().all()

                    is_soft_duplicate = False
                    for recent in recent_articles:
                        similarity = compute_title_similarity(raw_title, recent.title)
                        if similarity >= 0.75:
                            logger.info(
                                f"Pipeline: Skipping soft duplicate title similarity ({similarity:.2f}) for: '{raw_title}' (Matches recent ID: {recent.id})"
                            )
                            metrics["duplicates_skipped"] += 1
                            await publish_event("DEDUPE-ENGINE", f"Soft duplicate rejected: '{raw_title[:40]}'", "info")
                            is_soft_duplicate = True
                            break

                    if is_soft_duplicate:
                        # Save duplicate record to database as 'deduplicated' state for audit trails
                        new_article = RawArticle(
                            source_id=source.id,
                            title=raw_title,
                            url=normalized_url,
                            url_hash=url_hash,
                            title_hash=title_hash,
                            compressed_html=None,
                            clean_text=rss_summary,
                            article_metadata=json.dumps({"reason": "Soft duplicate title similarity check"}),
                            parser_version="1.0.0",
                            status="deduplicated",
                        )
                        db.add(new_article)
                        continue

                    # 3. HTML Extraction Strategy (Boilerplate-free extraction & scoring)
                    # Pass source-specific parser_profile config to html_agent
                    logger.info(f"Pipeline: Invoking HTMLAgent extraction pipeline for: {normalized_url}")
                    html_t0 = time.time()
                    extracted = await html_agent.extract_article(normalized_url, parser_config=parser_profile)
                    html_duration = round((time.time() - html_t0) * 1000.0, 2)

                    rss_fallback_used = False
                    if extracted and len(extracted["clean_text"]) > 150:
                        clean_body = extracted["clean_text"]
                        content_score = extracted["content_score"]
                        density_score = extracted["density_score"]
                        word_count = extracted["word_count"]
                        raw_html = extracted.get("raw_html") or item.get("raw_html") or clean_body
                        title_source = extracted.get("title") or raw_title
                    else:
                        # Fallback to RSS summary if HTML crawl fails or is too sparse
                        clean_body = rss_summary
                        content_score = 30.0
                        density_score = 0.50
                        word_count = len(rss_summary.split())
                        raw_html = item.get("raw_html") or rss_summary
                        title_source = raw_title
                        rss_fallback_used = True
                        logger.warning("Pipeline: HTML extraction failed/insufficient. Falling back to RSS summary.")

                    # 4. Adaptive Content Quality Pipeline & Extraction Confidence Scoring
                    meta_dict = {
                        "source_category": source.category,
                        "rss_fallback": rss_fallback_used,
                        "author": item.get("author"),
                        "publish_date": item.get("publish_date"),
                        "seo_keywords": "",
                    }

                    quality_res = evaluate_adaptive_quality(
                        title=title_source, content=clean_body, raw_html=raw_html, meta_dict=meta_dict
                    )

                    is_eligible_quality = quality_res["eligible"]
                    confidence_rating = quality_res.get("confidence", 0.0)

                    # Re-run relevance filter to verify tech topic keywords
                    is_relevant = check_pre_ai_ingestion_eligibility(
                        title=title_source, content=clean_body, source_credibility=source.credibility_score
                    )

                    is_eligible = is_eligible_quality and is_relevant

                    # Formal Ingestion State Machine transitions
                    if is_eligible:
                        status_state = "fetched"
                    else:
                        status_state = "filtered"
                        logger.info(
                            f"Pipeline: Article '{title_source[:50]}' rejected by quality pipeline (eligible_quality={is_eligible_quality}, relevant={is_relevant}). Reason: {quality_res.get('reason', 'Failed relevance check')}"
                        )

                    # 5. Raw HTML Storage Strategy & Compression (zlib Level 9)
                    compressed_payload = compress_content(raw_html)

                    # Metadata Separation (JSON serialized block)
                    meta_payload = {
                        "content_type": "text/html",
                        "response_time_ms": html_duration,
                        "content_score": content_score,
                        "density_score": density_score,
                        "word_count": word_count,
                        "extracted_at": current_time.isoformat(),
                        "parser": "HTMLAgent",
                        "rss_fallback": rss_fallback_used,
                        "extraction_confidence": confidence_rating,
                        "quality_metrics": {
                            "paragraph_count": quality_res.get("paragraph_count", 0),
                            "unique_ratio": quality_res.get("unique_ratio", 0.0),
                            "markup_ratio": quality_res.get("markup_ratio", 0.0),
                            "reason": quality_res.get("reason", ""),
                        },
                    }

                    if existing_article:
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
                        # Insert new raw article
                        new_article = RawArticle(
                            source_id=source.id,
                            title=title_source,
                            url=normalized_url,
                            url_hash=url_hash,
                            title_hash=title_hash,
                            compressed_html=compressed_payload,
                            clean_text=clean_body,
                            article_metadata=json.dumps(meta_payload),
                            parser_version="1.0.0",
                            status=status_state,
                        )
                        db.add(new_article)

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

    # Dispose of Agent pools cleanly
    await rss_agent.shutdown()
    await html_agent.shutdown()

    logger.info(f"Pipeline: Hardened Ingestion complete. Metrics: {metrics}")
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

    # 5. Reading time
    reading_time = calculate_reading_time(plain_text)

    # 6. Slugification
    slug = generate_slug(raw_art.title)

    # 7. Category mapping
    category_id = map_category_id(raw_art.title, plain_text)

    # 8. SEO Metadata
    seo_meta = generate_seo_metadata(raw_art.title, plain_text)

    # 9. Source attribution details
    source_name = source_obj.name if source_obj else "System Ingest"
    source_url = source_obj.url if source_obj else raw_art.url

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
            tags_string = proc_art.tags
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
                confidence = 99.0
            else:
                # Heuristic Fallback
                sentences = re.split(r"(?<=[.!?])\s+", plain_text)
                summary = " ".join(sentences[:2])
                if len(summary) > 280:
                    summary = summary[:277] + "..."
                if not summary:
                    summary = "No summary compiled yet."

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

    # 12. Write or Update in processed_articles
    existing_stmt = select(ProcessedArticle).where(ProcessedArticle.slug == slug)
    existing_res = await db.execute(existing_stmt)
    proc_art = existing_res.scalars().first()

    # Resolve exact category name for the real-time event metadata payload
    from app.models.article import Category

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
        proc_art.clean_html = clean_html_content
        proc_art.tags = tags_string
        proc_art.sentiment = sentiment
        proc_art.ai_confidence = confidence
        proc_art.reading_time = reading_time
        proc_art.seo_title = seo_meta["seo_title"]
        proc_art.seo_keywords = seo_meta["seo_keywords"]
        proc_art.readability_score = seo_meta["readability_score"]

        # Calculate updated scores
        impact = calculate_impact_score(raw_art.title, category_name, plain_text)
        freshness = calculate_freshness_score(proc_art.published_at)
        engagement = calculate_engagement_score(raw_art.article_metadata, source_cred)
        final = calculate_final_score(impact, freshness, engagement)

        proc_art.freshness_score = freshness
        proc_art.engagement_score = engagement
        proc_art.final_score = final
        proc_art.expires_at = proc_art.published_at + timedelta(hours=24)
        logger.info(f"Processor: Updated existing processed article record for slug: {slug}")
    else:
        # Create new processed record
        pub_at = datetime.now(timezone.utc)
        impact = calculate_impact_score(raw_art.title, category_name, plain_text)
        freshness = calculate_freshness_score(pub_at)
        engagement = calculate_engagement_score(raw_art.article_metadata, source_cred)
        final = calculate_final_score(impact, freshness, engagement)

        proc_art = ProcessedArticle(
            raw_article_id=raw_art.id,
            source_id=raw_art.source_id,
            category_id=category_id,
            title=raw_art.title,
            slug=slug,
            summary=summary,
            content=plain_text,
            source=source_name,
            source_name=source_name,
            source_url=source_url,
            clean_html=clean_html_content,
            tags=tags_string,
            sentiment=sentiment,
            ai_confidence=confidence,
            reading_time=reading_time,
            seo_title=seo_meta["seo_title"],
            seo_keywords=seo_meta["seo_keywords"],
            readability_score=seo_meta["readability_score"],
            published_status="published",
            published_at=pub_at,
            expires_at=pub_at + timedelta(hours=24),
            freshness_score=freshness,
            engagement_score=engagement,
            final_score=final,
        )
        db.add(proc_art)
        await db.flush()  # Ensure proc_art.id is populated for telemetry
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

    from app.tasks.article_intelligence import run_article_intelligence_pipeline
    from celery_app import download_thumbnail_task

    # Single orchestration task: Summary → Entities → Topics → Embedding → Cache bust
    proc_art.embedding_status = "queued"
    run_article_intelligence_pipeline.delay(proc_art.id)
    logger.info(f"Processor: Enqueued Article Intelligence Pipeline for ProcessedArticle ID {proc_art.id}")

    if not getattr(proc_art, "thumbnail_url", None):
        # Thumbnail download is kept separate — it's I/O work, not AI
        from app.core.config import settings
        download_thumbnail_task.delay(proc_art.id, candidates[:settings.MAX_THUMBNAIL_CANDIDATES] if candidates else [])
        logger.info(f"Processor: Enqueued background thumbnail download for ProcessedArticle ID {proc_art.id}")

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
        tags=proc_art.tags,
        category=category_name,
        published_status=proc_art.published_status
    )

    outbox_event = EventOutbox(
        event_type="ArticlePublished",
        payload=payload_model.model_dump(mode="json")
    )
    db.add(outbox_event)

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

    rss_agent = RSSIngestionAgent()
    html_agent = HTMLAgent()

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

        # 1. Fetch items dynamically using RSS Agent
        crawled_items = await rss_agent.crawl_feed(source.url)
        await publish_event("RSS-FORCE", f"Force crawled {len(crawled_items)} entries from {source.name}.", "success")

        if not crawled_items:
            raise RuntimeError("Crawl feed returned zero items.")

        crawled_items = crawled_items[:10]

        source.failure_count = 0
        source.health_state = "healthy"
        source.last_crawl_at = current_time
        source.successful_crawls += 1
        source.reliability_score = round((source.successful_crawls / source.total_crawls) * 100.0, 2)

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

            # Check unique composite constraint
            dup_stmt = select(RawArticle).where(
                (RawArticle.url_hash == url_hash) & (RawArticle.title_hash == title_hash)
            )
            dup_res = await db.execute(dup_stmt)
            existing_article = dup_res.scalars().first()

            if existing_article:
                if existing_article.status not in ("failed", "discovered"):
                    metrics["duplicates_skipped"] += 1
                    continue

            # Check title similarity past 24h
            yesterday = current_time - timedelta(days=1)
            soft_stmt = select(RawArticle).where(
                (RawArticle.scraped_at >= yesterday) & (RawArticle.status != "deduplicated")
            )
            soft_res = await db.execute(soft_stmt)
            recent_articles = soft_res.scalars().all()

            is_soft_duplicate = False
            for recent in recent_articles:
                similarity = compute_title_similarity(raw_title, recent.title)
                if similarity >= 0.75:
                    metrics["duplicates_skipped"] += 1
                    is_soft_duplicate = True
                    break

            if is_soft_duplicate:
                new_article = RawArticle(
                    source_id=source.id,
                    title=raw_title,
                    url=normalized_url,
                    url_hash=url_hash,
                    title_hash=title_hash,
                    compressed_html=None,
                    clean_text=rss_summary,
                    article_metadata=json.dumps({"reason": "Soft duplicate similarity check"}),
                    status="deduplicated",
                    scraped_at=current_time,
                )
                db.add(new_article)
                continue

            # Fetch HTML & Content Extraction
            import time
            html_t0 = time.time()
            extracted = await html_agent.extract_article(resolved_url)
            html_duration = int((time.time() - html_t0) * 1000)

            if not extracted:
                new_article = RawArticle(
                    source_id=source.id,
                    title=raw_title,
                    url=normalized_url,
                    url_hash=url_hash,
                    title_hash=title_hash,
                    compressed_html=None,
                    clean_text=rss_summary,
                    article_metadata=json.dumps({"error": "Failed to retrieve content"}),
                    status="failed",
                    scraped_at=current_time,
                )
                db.add(new_article)
                continue

            clean_body = extracted.get("clean_text") or rss_summary
            raw_html = extracted.get("raw_html") or rss_summary

            # Perform Quality Filtering on the full crawled text
            passes_filter = check_pre_ai_ingestion_eligibility(
                title=raw_title, content=clean_body, source_credibility=source.credibility_score
            )
            reason = "" if passes_filter else "Failed relevance check"
            if not passes_filter:
                new_article = RawArticle(
                    source_id=source.id,
                    title=raw_title,
                    url=normalized_url,
                    url_hash=url_hash,
                    title_hash=title_hash,
                    compressed_html=None,
                    clean_text=clean_body,
                    article_metadata=json.dumps({"reason": f"Quality filter: {reason}"}),
                    status="filtered",
                    scraped_at=current_time,
                )
                db.add(new_article)
                metrics["filtered_skipped"] += 1
                continue

            # Perform Adaptive Quality evaluation on the full crawled text
            q_metrics = evaluate_adaptive_quality(title=raw_title, content=clean_body, raw_html=raw_html, meta_dict={})

            if not q_metrics["eligible"]:
                new_article = RawArticle(
                    source_id=source.id,
                    title=raw_title,
                    url=normalized_url,
                    url_hash=url_hash,
                    title_hash=title_hash,
                    compressed_html=None,
                    clean_text=clean_body,
                    article_metadata=json.dumps({"reason": q_metrics.get("reason", "Failed quality checks")}),
                    status="filtered",
                    scraped_at=current_time,
                )
                db.add(new_article)
                metrics["filtered_skipped"] += 1
                continue

            # Compute confidence score
            word_count = len(clean_body.split()) if clean_body else 0
            parsing_w = 0.3 if word_count >= 150 else 0.15
            density_w = 0.3 if q_metrics.get("unique_ratio", 0) >= 0.45 else 0.15
            trunc_w = 0.3
            meta_w = 0.1 if len(raw_title) >= 15 else 0.05
            confidence = round((parsing_w + density_w + trunc_w + meta_w) * 100.0, 2)

            compressed_data = compress_content(raw_html)
            meta_payload = {
                "word_count": word_count,
                "response_time_ms": html_duration,
                "extraction_confidence": confidence,
                "quality_metrics": q_metrics,
            }

            new_article = RawArticle(
                source_id=source.id,
                title=raw_title,
                url=normalized_url,
                url_hash=url_hash,
                title_hash=title_hash,
                compressed_html=compressed_data,
                clean_text=clean_body,
                article_metadata=json.dumps(meta_payload),
                status="fetched",
                scraped_at=current_time,
            )
            db.add(new_article)
            metrics["articles_saved"] += 1

        await db.commit()
        await publish_event(
            "INGESTION", f"Force crawl complete. Source '{source.name}' successfully parsed.", "success"
        )

    except Exception as e:
        logger.error(f"Pipeline: Force crawl failed for source {source.name}: {e}", exc_info=True)
        await db.rollback()
        metrics["status"] = "error"
        metrics["message"] = str(e)

    finally:
        await rss_agent.shutdown()
        await html_agent.shutdown()

    return metrics
