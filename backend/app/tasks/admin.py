import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

from celery_app import celery_app
from sqlalchemy import select
from app.core.database import AsyncSessionLocal as SessionLocal
from app.models.article import RawArticle
from app.models.source import Source
from app.services.ingestion.extraction_service import ExtractionService
from app.services.ingestion.filter import evaluate_adaptive_quality, evaluate_relevance
from app.services.ingestion.utils import compress_content
from app.editorial.policy import PolicyLoader

logger = logging.getLogger("tech_news.tasks.admin")

async def _replay_article_async(raw_article_id: int, session_maker) -> bool:
    """
    Re-runs the canonical acquisition and relevance pipeline for a single filtered RawArticle.
    If it passes, it updates the record and triggers editorial processing.
    """
    async with session_maker() as db:
        stmt = select(RawArticle, Source).join(Source).where(RawArticle.id == raw_article_id)
        res = await db.execute(stmt)
        row = res.first()
        if not row:
            logger.error(f"Replay: RawArticle {raw_article_id} not found.")
            return False
            
        raw_art, source = row
        
        # Ensure idempotent
        if raw_art.status not in ("filtered", "discovered"):
            logger.info(f"Replay: Skipping RawArticle {raw_article_id} because status is {raw_art.status}")
            return False

        logger.info(f"Replay: Invoking ExtractionService for: {raw_art.url}")
        
        extraction_service = ExtractionService()
        
        parser_profile = {}
        if source.parser_config:
            try:
                parser_profile = json.loads(source.parser_config)
            except Exception as pe:
                logger.warning(f"Replay: Failed to parse parser_config JSON for '{source.name}': {pe}")

        html_t0 = time.time()
        has_content, extracted = await extraction_service.extract_content(
            raw_art.url, parser_config=parser_profile, source_name=source.name
        )
        html_duration = round((time.time() - html_t0) * 1000.0, 2)

        # Fallback summary
        rss_summary = raw_art.clean_text if raw_art.clean_text else ""
        raw_title = raw_art.title

        raw_html = extracted.get("raw_html", "")

        rss_fallback_used = False
        if has_content:
            clean_body = extracted["clean_text"]
            content_score = extracted.get("content_score", 50.0)
            density_score = extracted.get("density_score", 0.5)
            word_count = extracted.get("word_count", len(clean_body.split()))
            title_source = extracted.get("title") or raw_title
        else:
            clean_body = rss_summary
            content_score = 30.0
            density_score = 0.50
            word_count = len(rss_summary.split())
            title_source = raw_title
            rss_fallback_used = True
            
        if not raw_html:
            raw_html = rss_summary

        policy = PolicyLoader.get_policy()
        allowed_rss_fallback_sources = set(policy.get("allow_rss_fallback", []))

        meta_dict = {
            "source_category": source.category,
            "source_name": source.name,
            "rss_fallback": rss_fallback_used,
            "allow_rss_fallback": source.name in allowed_rss_fallback_sources,
            "author": "",
            "publish_date": "",
            "seo_keywords": "",
        }

        quality_res = evaluate_adaptive_quality(
            title=title_source, content=clean_body, raw_html=raw_html, meta_dict=meta_dict
        )

        is_eligible_quality = quality_res["eligible"]
        confidence_rating = quality_res.get("confidence", 0.0)
        is_degraded = quality_res.get("is_degraded", False)

        if is_degraded:
            is_relevant = True
            relevance_reason = ""
        else:
            is_relevant, relevance_reason = evaluate_relevance(
                title=title_source, content=clean_body, source_category=source.category
            )

        is_eligible = is_eligible_quality and is_relevant

        filter_reason = None
        if not is_eligible:
            if not is_eligible_quality:
                if quality_res.get("reason", "").startswith("Insufficient content length"):
                    filter_reason = "RSS_CONTENT_TOO_SHORT"
                elif quality_res.get("reason", "").startswith("Truncated"):
                    filter_reason = "CANONICAL_EXTRACTION_EMPTY"
                else:
                    filter_reason = "LOW_INFORMATION_DENSITY"
            else:
                filter_reason = relevance_reason

        current_time = datetime.now(timezone.utc)
        compressed_payload = compress_content(raw_html)

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
                "is_degraded": is_degraded,
            },
            "content_source": "RSS_FALLBACK" if is_degraded else ("RSS" if rss_fallback_used else "HTML"),
            "quality_state": "DEGRADED" if is_degraded else "NORMAL",
            "needs_html_refresh": is_degraded,
        }

        raw_art.title = title_source
        raw_art.compressed_html = compressed_payload
        raw_art.clean_text = clean_body
        raw_art.article_metadata = json.dumps(meta_payload)
        raw_art.scraped_at = current_time
        raw_art.filter_reason = filter_reason
        
        if is_eligible:
            raw_art.status = "fetched"
            logger.info(f"Replay: Article {raw_article_id} PASSED checks. Enqueueing processing.")
        else:
            raw_art.retry_count = raw_art.retry_count + 1
            raw_art.last_retry_at = current_time
            
            if raw_art.retry_count >= 3:
                raw_art.status = "dead_letter"
                raw_art.dead_letter_reason = filter_reason
                raw_art.dead_letter_at = current_time
                logger.warning(f"Replay: Article {raw_article_id} failed 3 times. Moving to dead-letter state.")
            else:
                raw_art.status = "filtered"
                logger.info(f"Replay: Article {raw_article_id} FAILED checks. Reason: {filter_reason}. Retry {raw_art.retry_count}/3")

        await db.commit()

        if is_eligible:
            # Re-enter the canonical pipeline AI processing step
            from app.services.ingestion.pipeline import process_raw_article_to_editorial
            await process_raw_article_to_editorial(db, raw_article_id)
            await db.commit()
            return True
            
        return False

@celery_app.task(name="tasks.admin.replay_filtered_articles")
def replay_filtered_articles(article_ids: Optional[List[int]] = None, filter_reason: Optional[str] = None):
    """
    Celery task to deterministically replay filtered articles.
    Re-runs canonical extraction and relevance evaluation.
    """
    from celery_app import CeleryAsyncSessionLocal, worker_loop
    import asyncio
    
    if CeleryAsyncSessionLocal is None:
        # Fallback for synchronous test execution outside the worker
        from app.core.database import AsyncSessionLocal
        db_factory = AsyncSessionLocal
        loop = asyncio.get_event_loop()
    else:
        db_factory = CeleryAsyncSessionLocal
        loop = worker_loop

    async def _run():
        async with db_factory() as db:
            stmt = select(RawArticle.id).where(RawArticle.status == "filtered")
            if article_ids:
                stmt = stmt.where(RawArticle.id.in_(article_ids))
            if filter_reason:
                if filter_reason == "UNKNOWN":
                    stmt = stmt.where(RawArticle.filter_reason.is_(None))
                else:
                    stmt = stmt.where(RawArticle.filter_reason == filter_reason)
                
            # Limit batch size to 50 for safety
            stmt = stmt.limit(50)
            res = await db.execute(stmt)
            ids = res.scalars().all()
            
        logger.info(f"Replay task found {len(ids)} articles to replay.")
        for aid in ids:
            await _replay_article_async(aid, db_factory)

    loop.run_until_complete(_run())


@celery_app.task(name="tasks.recovery.autonomous_ingestion_recovery")
def autonomous_ingestion_recovery():
    """
    Autonomous recovery loop to automatically detect retryable pipeline starvation
    and retry eligible filtered records using exponential backoff.
    """
    from celery_app import CeleryAsyncSessionLocal, worker_loop
    import asyncio
    from datetime import datetime, timezone, timedelta
    
    if CeleryAsyncSessionLocal is None:
        from app.core.database import AsyncSessionLocal
        db_factory = AsyncSessionLocal
        loop = asyncio.get_event_loop()
    else:
        db_factory = CeleryAsyncSessionLocal
        loop = worker_loop

    async def _run():
        async with db_factory() as db:
            current_time = datetime.now(timezone.utc)
            
            stmt = select(RawArticle.id).where(
                RawArticle.status == "filtered",
                RawArticle.retry_count < 3
            ).limit(20)
            
            res = await db.execute(stmt)
            ids = res.scalars().all()
            
        logger.info(f"Autonomous Recovery: Found {len(ids)} filtered articles to retry.")
        for aid in ids:
            await _replay_article_async(aid, db_factory)

    loop.run_until_complete(_run())
