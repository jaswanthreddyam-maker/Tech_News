import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
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


def calculate_final_score(impact: float, freshness: float, engagement: float) -> float:
    """
    Calculates the final composite score.
    Formula: impact * 0.60 + freshness * 0.25 + engagement * 0.15
    """
    return impact * 0.60 + freshness * 0.25 + engagement * 0.15


async def expire_old_articles(db: AsyncSession) -> int:
    """
    Scans the database and marks any active articles exceeding their 24h hard expiry as archived.
    Returns the count of articles archived.
    """
    now = datetime.now(timezone.utc)

    # Select articles that have expired but are not yet marked as archived
    stmt = select(ProcessedArticle).where(
        and_(
            ProcessedArticle.is_archived == False,
            or_(ProcessedArticle.expires_at <= now, ProcessedArticle.published_at <= now - timedelta(hours=24)),
        )
    )
    res = await db.execute(stmt)
    expired = res.scalars().all()

    for art in expired:
        art.is_archived = True
        art.published_status = "archived"
        logger.info(f"News Ranking: Hard-expired article ID {art.id} ('{art.title}') - moved to archive.")

    if expired:
        await db.commit()

    return len(expired)


async def rank_articles(db: AsyncSession) -> dict:
    """
    Performs the 12-hour evaluation run:
    1. Expires old articles (> 24 hours).
    2. Recalculates scores for all remaining active articles.
    3. Triggers homepage feed and trend updates.
    """
    now = datetime.now(timezone.utc)

    # 1. Expire old articles
    expired_count = await expire_old_articles(db)

    # 2. Fetch all active articles (not archived and not expired)
    cutoff_24h = now - timedelta(hours=24)
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
                ProcessedArticle.published_status == "published",
                ProcessedArticle.published_at >= cutoff_24h,
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
        final = calculate_final_score(impact, freshness, engagement)

        # Update expires_at if it's not set
        if not art.expires_at:
            art.expires_at = art.published_at + timedelta(hours=24)

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
    cutoff_24h = now - timedelta(hours=24)
    cutoff_12h = now - timedelta(hours=12)

    # Query all active published articles
    stmt = (
        select(ProcessedArticle)
        .options(selectinload(ProcessedArticle.category))
        .where(
            and_(
                ProcessedArticle.is_archived == False,
                ProcessedArticle.published_status == "published",
                ProcessedArticle.published_at >= cutoff_24h,
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
