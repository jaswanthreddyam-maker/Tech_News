"""
Operational Recovery & Controlled Re-acquisition Module.

Implements bounded, idempotent content re-acquisition for weak articles with zero direct DB hacks:
  - Case A (Filtered RawArticle): Re-runs process_raw_article via canonical pipeline.
  - Case B (Existing Published Article): Re-acquires canonical HTML, updates ProcessedArticle,
    increments content_revision, and re-emits domain event / projection.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel
from app.services.ingestion.extraction_service import ExtractionService
from app.services.ingestion.acquisition_policy import ContentAcquisitionPolicy

logger = logging.getLogger("tech_news.tasks.recovery")


async def reacquire_weak_articles(
    db: AsyncSession,
    batch_size: int = 10,
    article_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Executes bounded, idempotent re-acquisition for weak articles.
    Returns operational metrics dict.
    """
    batch_limit = min(max(1, batch_size), 10)
    extraction_service = ExtractionService()
    policy = ContentAcquisitionPolicy()

    metrics = {
        "candidate_count": 0,
        "reacquired_case_a": 0,
        "reacquired_case_b": 0,
        "rejected_count": 0,
        "errors": [],
    }

    # -------------------------------------------------------------------------
    # Case A: Filtered RawArticle Records
    # -------------------------------------------------------------------------
    raw_stmt = select(RawArticle).where(RawArticle.status == "filtered")
    if article_ids:
        raw_stmt = raw_stmt.where(RawArticle.id.in_(article_ids))
    raw_stmt = raw_stmt.limit(batch_limit)

    raw_res = await db.execute(raw_stmt)
    raw_candidates = raw_res.scalars().all()

    from app.services.ingestion.pipeline import process_raw_article
    for raw in raw_candidates:
        metrics["candidate_count"] += 1
        try:
            logger.info(f"Recovery: Re-running pipeline for Case A RawArticle ID {raw.id}")
            res = await process_raw_article(db, raw.id)
            if res.get("status") in ("fetched", "processed", "success"):
                metrics["reacquired_case_a"] += 1
            else:
                metrics["rejected_count"] += 1
        except Exception as e:
            logger.error(f"Recovery: Exception in Case A re-acquisition for RawArticle {raw.id}: {e}")
            metrics["errors"].append(f"RawArticle {raw.id}: {str(e)}")

    # -------------------------------------------------------------------------
    # Case B: Existing ProcessedArticles with Weak Content (< 100 words)
    # -------------------------------------------------------------------------
    proc_stmt = select(ProcessedArticle).where(ProcessedArticle.content != None)
    if article_ids:
        proc_stmt = proc_stmt.where(ProcessedArticle.id.in_(article_ids))
    proc_stmt = proc_stmt.limit(batch_limit)

    proc_res = await db.execute(proc_stmt)
    proc_candidates = proc_res.scalars().all()

    for proc in proc_candidates:
        words = len((proc.content or "").split())
        if words >= 150:
            continue  # Already substantive

        metrics["candidate_count"] += 1
        url = proc.source_url or proc.slug
        if not url or not url.startswith("http"):
            continue

        try:
            logger.info(f"Recovery: Case B canonical fetch for ProcessedArticle ID {proc.id} (Current words: {words})")
            extraction_res = await extraction_service.extract_content(url, source_name=proc.source_name)
            decision = policy.evaluate(
                rss_title=proc.title,
                rss_text=proc.summary,
                extraction_result=extraction_res,
                source_policy={"allow_weak_rss_fallback": False}
            )

            if decision.decision == "CANONICAL_SELECTED" and decision.selected_content:
                new_revision = (proc.content_revision or 1) + 1
                proc.content = decision.selected_content
                proc.content_revision = new_revision
                
                meta = {}
                if proc.article_metadata:
                    try:
                        meta = json.loads(proc.article_metadata) if isinstance(proc.article_metadata, str) else proc.article_metadata
                    except Exception:
                        pass

                meta.update({
                    "content_source": "canonical_html",
                    "acquisition_decision": "CANONICAL_SELECTED",
                    "content_revision": new_revision,
                    "canonical_word_count": decision.word_count,
                    "reacquired_at": proc.published_at.isoformat() if proc.published_at else None,
                })
                proc.article_metadata = json.dumps(meta)

                # Project update to ArticleReadModel
                read_stmt = select(ArticleReadModel).where(ArticleReadModel.id == str(proc.id))
                read_res = await db.execute(read_stmt)
                read_art = read_res.scalars().first()
                if read_art:
                    read_art.content = proc.content
                    read_art.summary = proc.summary

                await db.commit()
                metrics["reacquired_case_b"] += 1
                logger.info(f"Recovery: Successfully re-acquired canonical content for ProcessedArticle ID {proc.id} (rev={new_revision}, words={decision.word_count})")
            else:
                metrics["rejected_count"] += 1
                logger.info(f"Recovery: Case B re-acquisition rejected for ProcessedArticle ID {proc.id}. Reason: {decision.fallback_reason}")

        except Exception as e:
            logger.error(f"Recovery: Exception in Case B re-acquisition for ProcessedArticle {proc.id}: {e}")
            metrics["errors"].append(f"ProcessedArticle {proc.id}: {str(e)}")

    return metrics
