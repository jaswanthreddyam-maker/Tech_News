import json
import logging
import os
import yaml
from pathlib import Path
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import log_audit
from app.core.config import settings
from app.core.event_bus import publish_event
from app.core.redis import get_redis_client
from app.models.article import Category, ProcessedArticle

logger = logging.getLogger("tech_news.ranking")

# Configurable mappings from settings
COMPANY_WEIGHTS = settings.RANKING_COMPANY_WEIGHTS
TECH_KEYWORDS = settings.RANKING_TECH_KEYWORDS
REDUCTIONS = settings.RANKING_REDUCTIONS


def get_lifecycle_policy() -> dict:
    default_policy = {
        "minimum_ttl_hours": 12,
        "maximum_ttl_hours": 72,
        "editorial_weight": 0.8,
        "freshness_weight": 0.2,
        "minimum_article_floor": 5,
    }
    try:
        base_dir = getattr(settings, "BASE_DIR", None)
        if base_dir:
            policy_path = Path(base_dir) / "app" / "editorial" / "lifecycle_policy.yaml"
        else:
            policy_path = Path(__file__).resolve().parent.parent / "editorial" / "lifecycle_policy.yaml"

        if policy_path.exists():
            with open(policy_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config and "article_lifecycle" in config:
                    default_policy.update(config["article_lifecycle"])
    except Exception as e:
        logger.warning(f"Failed to load lifecycle_policy.yaml: {e}")
    return default_policy


def calculate_article_ttl(editorial_score: float, freshness_score: float) -> timedelta:
    policy = get_lifecycle_policy()
    min_ttl = float(policy.get("minimum_ttl_hours", 12))
    max_ttl = float(policy.get("maximum_ttl_hours", 72))
    ed_weight = float(policy.get("editorial_weight", 0.8))
    fr_weight = float(policy.get("freshness_weight", 0.2))
    
    ttl_score = (editorial_score * ed_weight) + (freshness_score * fr_weight)
    
    # Scale TTL based on score (0 to 100)
    calculated_ttl = (ttl_score / 100.0) * max_ttl
    
    # Clamp between min and max
    final_ttl_hours = max(min_ttl, min(max_ttl, calculated_ttl))
    
    return timedelta(hours=final_ttl_hours)


def calculate_impact_score(title: str, category: str, content: str) -> float:
    """
    Calculates an impact score (0 - 100) based on company presence, technology keywords,
    and general category boosts/reductions.
    """
    score = 40.0  # Base score
    title_lower = title.lower()
    content_lower = content.lower()

    # 1. Company Importance
    company_contrib = 0.0
    for company, weight in COMPANY_WEIGHTS.items():
        if company in title_lower or company in content_lower:
            company_contrib = max(company_contrib, weight)
    score += company_contrib

    # 2. Technology Importance
    tech_contrib = 0.0
    for kw, weight in TECH_KEYWORDS.items():
        if kw in title_lower or kw in content_lower:
            tech_contrib = max(tech_contrib, weight)
    score += tech_contrib

    # 3. Category Boost
    cat_lower = category.lower()
    if "intelligence" in cat_lower or "ai" in cat_lower or "cybersecurity" in cat_lower or "security" in cat_lower:
        score += 10.0

    # 4. Reductions for low-impact stories
    for kw, reduction in REDUCTIONS.items():
        if kw in title_lower or kw in content_lower:
            score += reduction  # reduction is negative

    return max(0.0, min(100.0, score))


def calculate_freshness_score(published_at: datetime) -> float:
    """
    Calculates freshness score (0 - 100) based on age, decaying naturally over time.
    0-2 Hours   = 100
    2-6 Hours   = 80
    6-12 Hours  = 60
    12-18 Hours = 40
    18-24 Hours = 20
    24+ Hours   = 0
    """
    now = datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age_hours = (now - published_at).total_seconds() / 3600.0

    if age_hours < 0:
        return 100.0  # Future post (safeguard)
    elif age_hours <= 2.0:
        return 100.0
    elif age_hours <= 6.0:
        return 80.0
    elif age_hours <= 12.0:
        return 60.0
    elif age_hours <= 18.0:
        return 40.0
    elif age_hours <= 24.0:
        return 20.0
    else:
        return 0.0


def calculate_engagement_score(metadata_str: str | None, source_credibility: int) -> float:
    """
    Calculates engagement score (0 - 100) based on social signals and source credibility.
    """
    # 40% from source credibility baseline
    score = (source_credibility or 50) * 0.40

    # 60% from raw metadata social signals (Reddit, HN, Mentions)
    social_score = 0.0
    if metadata_str:
        try:
            meta = json.loads(metadata_str)
            reddit_score = float(meta.get("reddit_score", 0) or meta.get("reddit_upvotes", 0) or 0)
            hn_score = float(meta.get("hn_score", 0) or meta.get("hn_points", 0) or 0)
            mentions = float(meta.get("mentions", 0) or 0)
            social_score = reddit_score + (hn_score * 1.5) + (mentions * 5.0)
        except Exception:
            pass

    # Scale social contribution to max 60 points
    social_contrib = min(60.0, social_score / 10.0)
    score += social_contrib

    return max(0.0, min(100.0, score))


def calculate_quality_score(content: str, metadata_str: str | None) -> float:
    """
    Calculates a quality score (0 - 100) based on content depth (word/paragraph count)
    and extraction confidence. Penalizes short RSS summaries.
    """
    score = 0.0
    
    word_count = len(content.split()) if content else 0
    if word_count < 50:
        score += 20.0  # RSS summary
    elif word_count < 200:
        score += 40.0
    elif word_count < 500:
        score += 70.0
    else:
        score += 90.0

    if metadata_str:
        try:
            meta = json.loads(metadata_str)
            confidence = float(meta.get("extraction_confidence", 0.0) or 0.0)
            # Add up to 10 bonus points for high confidence extraction
            score += min(10.0, confidence / 10.0)
        except Exception:
            pass

    return max(0.0, min(100.0, score))


def calculate_final_score(impact: float, freshness: float, engagement: float, quality: float = 0.0) -> float:
    """
    Calculates the final composite score.
    Formula: impact * 0.45 + freshness * 0.30 + engagement * 0.15 + quality * 0.10
    """
    return impact * 0.45 + freshness * 0.30 + engagement * 0.15 + quality * 0.10


async def expire_articles(db: AsyncSession) -> dict:
    """
    Non-destructive article expiration.

    Expired articles are marked with is_expired=True on ProcessedArticle
    and publication_status='EXPIRED' on ArticleReadModel.

    INVARIANTS:
    - RawArticle is NEVER deleted (canonical crawl evidence).
    - ProcessedArticle is NEVER deleted (source-of-truth).
    - ArticleReadModel is NEVER deleted (preserves article detail pages).
    - Circuit breaker prevents total editorial depletion.
    - This function is safe to call at any frequency.
    """
    now = datetime.now(timezone.utc)
    from app.models.article import ArticleReadModel

    policy = get_lifecycle_policy()
    MINIMUM_FLOOR = int(policy.get("minimum_article_floor", 5))

    metrics = {
        "expired_articles_total": 0,
        "circuit_breaker_activated": False,
        "expire_duration_ms": 0,
    }

    start_time = datetime.now()
    homepage_affected = False

    # ── Circuit Breaker: explicit active_before / expiring_now / active_after ──
    active_before_result = await db.execute(
        select(func.count(ProcessedArticle.id))
        .where(
            ProcessedArticle.is_expired == False,
            ProcessedArticle.is_archived == False,
            ProcessedArticle.published_status == "published",
            or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now),
        )
    )
    active_before = active_before_result.scalar() or 0

    expiring_result = await db.execute(
        select(func.count(ProcessedArticle.id))
        .where(
            ProcessedArticle.expires_at <= now,
            ProcessedArticle.is_expired == False,
            ProcessedArticle.is_archived == False,
            ProcessedArticle.published_status == "published",
        )
    )
    expiring_now = expiring_result.scalar() or 0

    active_after = active_before - expiring_now

    if expiring_now > 0 and active_after < MINIMUM_FLOOR:
        logger.warning(
            f"CIRCUIT BREAKER: Expiring {expiring_now} articles would reduce "
            f"inventory from {active_before} to {active_after} "
            f"(below floor of {MINIMUM_FLOOR}). Extending TTL by 6h instead."
        )
        await db.execute(
            update(ProcessedArticle)
            .where(
                ProcessedArticle.expires_at <= now,
                ProcessedArticle.is_expired == False,
                ProcessedArticle.is_archived == False,
                ProcessedArticle.published_status == "published",
            )
            .values(expires_at=now + timedelta(hours=6))
        )
        await db.commit()
        metrics["circuit_breaker_activated"] = True
        metrics["expire_duration_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
        return metrics

    # ── Non-destructive expiration (batched) ──
    while True:
        stmt = select(
            ProcessedArticle.id,
            ProcessedArticle.source_name,
            ProcessedArticle.final_score,
            ProcessedArticle.expires_at,
        ).where(
            ProcessedArticle.expires_at <= now,
            ProcessedArticle.is_expired == False,
            ProcessedArticle.is_archived == False,
            ProcessedArticle.published_status == "published",
        ).limit(500)

        res = await db.execute(stmt)
        expired_articles = res.all()

        if not expired_articles:
            break

        expired_ids = [art.id for art in expired_articles]

        # 1. Check if any are in homepage projection
        from app.models.projection import HomepageProjection
        try:
            proj_stmt = select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1)
            proj_res = await db.execute(proj_stmt)
            proj = proj_res.scalars().first()
        except Exception:
            await db.rollback()
            proj = None
            homepage_affected = True

        if proj and proj.stories_json:
            if isinstance(proj.stories_json, dict) and "feed" in proj.stories_json:
                feed_ids = [item.get("id") for item in proj.stories_json["feed"]]
            elif isinstance(proj.stories_json, list):
                feed_ids = [item.get("id") for item in proj.stories_json]
            else:
                feed_ids = []

            if any(str(eid) in feed_ids for eid in expired_ids):
                homepage_affected = True

        # 2. Audit log
        for art in expired_articles:
            await log_audit(
                db,
                action="ArticleExpired",
                resource=f"ProcessedArticle:{art.id}",
                user_id=None,
                metadata={
                    "publisher": art.source_name,
                    "score": float(art.final_score) if art.final_score else 0.0,
                    "expired_at": art.expires_at.isoformat() if art.expires_at else None,
                    "reason": "TTL_EXPIRED",
                },
            )

        # 3. Non-destructive state transitions
        try:
            # Mark ProcessedArticle as expired (editorial visibility change)
            await db.execute(
                update(ProcessedArticle)
                .where(ProcessedArticle.id.in_(expired_ids))
                .values(is_expired=True, expired_at=now)
            )

            # Preserve ArticleReadModel publication_status='PUBLISHED' for permalinks & emergency fallback.
            # Do not mutate publication_status to 'EXPIRED' to prevent read model breakage.

            # DO NOT delete RawArticle — canonical crawl evidence
            # DO NOT delete ProcessedArticle — source-of-truth

            await db.commit()
            metrics["expired_articles_total"] += len(expired_ids)

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to expire batch of articles: {e}")
            break

    # Rebuild homepage conditionally via EventOutbox
    if homepage_affected:
        from app.core.events.models import EventOutbox
        event = EventOutbox(
            event_type="ProjectionRefreshRequested",
            payload={
                "projection_type": "ALL",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "reason": "Expired articles removed from homepage feed",
            },
        )
        db.add(event)

    metrics["expire_duration_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
    return metrics


# Keep backward-compatible alias so any external callers don't break
async def expire_and_purge_articles(db: AsyncSession) -> dict:
    """Backward-compatible alias for expire_articles()."""
    return await expire_articles(db)


async def expire_old_articles(db: AsyncSession) -> int:
    """Alias for expire_articles() that returns just the count."""
    metrics = await expire_articles(db)
    return metrics.get("expired_articles_total", 0)


async def rank_articles(db: AsyncSession) -> dict:
    """
    Performs the 12-hour evaluation run:
    1. Expires old articles (> 24 hours).
    2. Recalculates scores for all remaining active articles.
    3. Triggers homepage feed and trend updates.
    """
    now = datetime.now(timezone.utc)

    # 1. Expire old articles
    expire_metrics = await expire_articles(db)
    expired_count = expire_metrics.get("expired_articles_total", 0)

    # 2. Fetch all active articles (not archived and not expired)
    stmt = (
        select(ProcessedArticle)
        .options(
            selectinload(ProcessedArticle.category),
            selectinload(ProcessedArticle.raw_article),
            selectinload(ProcessedArticle.source_ref),
        )
        .where(
            and_(
                ProcessedArticle.is_archived == False,
                ProcessedArticle.is_expired == False,
                ProcessedArticle.published_status == "published",
                or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now),
            )
        )
    )

    res = await db.execute(stmt)
    active_articles = res.scalars().all()

    total_evaluated = len(active_articles)
    impact_sum = 0.0
    final_sum = 0.0

    # 3. Recalculate scores for each active article
    for art in active_articles:
        category_name = art.category.name if art.category else "General"
        raw_meta = art.raw_article.article_metadata if art.raw_article else None

        # Determine source credibility
        source_cred = 80
        if art.source_ref:
            source_cred = art.source_ref.credibility_score

        impact = calculate_impact_score(art.title, category_name, art.content)
        freshness = calculate_freshness_score(art.published_at)
        engagement = calculate_engagement_score(raw_meta, source_cred)
        quality = calculate_quality_score(art.content, raw_meta)
        final = calculate_final_score(impact, freshness, engagement, quality)

        # Calculate dynamic TTL based on blended scores
        ttl_delta = calculate_article_ttl(editorial_score=final, freshness_score=freshness)

        # TTL baseline: use published_at (not scraped_at) for consistent behavior
        baseline = art.published_at or art.created_at or now
        new_expires = baseline + ttl_delta

        # NEVER-SHORTEN INVARIANT: ranking may only extend, never reduce TTL
        if art.expires_at is None or new_expires > art.expires_at:
            art.expires_at = new_expires

        art.freshness_score = freshness
        art.engagement_score = engagement
        art.final_score = final

        impact_sum += impact
        final_sum += final

    await db.commit()

    # Calculate averages
    avg_impact = (impact_sum / total_evaluated) if total_evaluated > 0 else 0.0
    avg_final = (final_sum / total_evaluated) if total_evaluated > 0 else 0.0

    # 4. Rebuild the Pre-ranked Feed Cache in Redis
    selected_ids = await rebuild_homepage_feed(db, limit=15)

    # 5. Refresh Telemetry metrics in Redis
    metrics = {
        "articles_evaluated": total_evaluated + expired_count,
        "active_articles": total_evaluated,
        "expired_articles": expired_count,
        "avg_impact_score": round(avg_impact, 2),
        "avg_final_score": round(avg_final, 2),
        "last_run": now.isoformat(),
        "next_run": (now + timedelta(hours=12)).isoformat(),
    }

    try:
        redis = get_redis_client()
        await redis.set("ranking_engine_metrics", json.dumps(metrics))
    except Exception as redis_err:
        logger.warning(f"Failed to update ranking metrics in Redis: {redis_err}")

    # Find a valid user ID to log audit (FK constraint requirement)
    system_user_id = None
    try:
        from app.models.user import User

        user_stmt = select(User.id).limit(1)
        user_res = await db.execute(user_stmt)
        system_user_id = user_res.scalar()
    except Exception as user_err:
        logger.warning(f"Failed to fetch system user for audit logging: {user_err}")

    # 6. Audit logging
    await log_audit(
        db=db,
        user_id=system_user_id,
        action="RANKING_RUN",
        resource="news_ranking_engine",
        metadata={
            "evaluated": total_evaluated + expired_count,
            "selected": len(selected_ids),
            "expired": expired_count,
            "avg_impact_score": avg_impact,
            "avg_final_score": avg_final,
        },
    )

    # 7. Emit real-time SSE event
    try:
        await publish_event(
            "INGESTION",
            f"News ranking engine cycle complete. Evaluated: {total_evaluated}, Expired: {expired_count}.",
            "success",
            metrics,
        )
    except Exception as sse_err:
        logger.warning(f"Failed to publish SSE ranking telemetry update: {sse_err}")

    return metrics


async def rebuild_homepage_feed(db: AsyncSession, limit: int = 15) -> list[int]:
    """
    Computes the pre-ranked homepage feed using the 70% current / 30% previous window rule.
    Caches the selected article IDs in Redis to prevent expensive on-load queries.
    """
    articles = await get_ranked_homepage_articles(db, category_slug=None, limit=limit)
    selected_ids = [art.id for art in articles]

    if not selected_ids:
        logger.warning(
            "News Ranking: Rebuilt homepage feed yielded 0 articles. Skipping Redis cache overwrite to prevent feed wipe."
        )
        return []

    try:
        redis = get_redis_client()
        await redis.set("homepage_article_ids", json.dumps(selected_ids))
        logger.info(
            f"News Ranking: Pre-ranked homepage feed rebuilt and cached in Redis. Slots filled: {len(selected_ids)}"
        )
    except Exception as e:
        logger.warning(f"Failed to cache homepage feed in Redis: {e}")

    return selected_ids


async def get_ranked_homepage_articles(
    db: AsyncSession, category_slug: str | None = None, limit: int = 10
) -> list[ProcessedArticle]:
    """
    Retrieves ranked active articles based on the 70% current / 30% previous window rule.
    """
    now = datetime.now(timezone.utc)
    cutoff_12h = now - timedelta(hours=12)

    # Query all active published articles
    stmt = (
        select(ProcessedArticle)
        .options(selectinload(ProcessedArticle.category))
        .where(
            and_(
                ProcessedArticle.is_archived == False,
                ProcessedArticle.is_expired == False,
                ProcessedArticle.published_status == "published",
                or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now),
            )
        )
    )

    if category_slug:
        stmt = stmt.join(Category).where(Category.slug == category_slug)

    res = await db.execute(stmt)
    all_articles = res.scalars().all()

    current_window = []
    previous_window = []

    for art in all_articles:
        pub_at = art.published_at
        if pub_at.tzinfo is None:
            pub_at = pub_at.replace(tzinfo=timezone.utc)

        if pub_at >= cutoff_12h:
            current_window.append(art)
        else:
            previous_window.append(art)

    # Sort pools by final_score descending
    current_window.sort(key=lambda x: float(x.final_score or 0.0), reverse=True)
    previous_window.sort(key=lambda x: float(x.final_score or 0.0), reverse=True)

    # Enforce 70% current / 30% previous distribution
    target_current = int(limit * 0.7)
    target_prev = limit - target_current

    selected_current = current_window[:target_current]
    selected_prev = previous_window[:target_prev]

    # Backfill if one pool has insufficient elements
    if len(selected_current) < target_current:
        extra_needed = target_current - len(selected_current)
        selected_prev = previous_window[: target_prev + extra_needed]
    elif len(selected_prev) < target_prev:
        extra_needed = target_prev - len(selected_prev)
        selected_current = current_window[: target_current + extra_needed]

    # Combine backfilled lists
    final_selection = selected_current + selected_prev

    # Sort combined result by final_score descending
    final_selection.sort(key=lambda x: float(x.final_score or 0.0), reverse=True)

    return final_selection[:limit]
