import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.models.article import Category, ProcessedArticle
from app.services.ranking.news_ranking_engine import (
    expire_old_articles,
    get_ranked_homepage_articles,
    rank_articles,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_ranking")


async def get_or_create_category(db: AsyncSession) -> Category:
    stmt = select(Category).limit(1)
    res = await db.execute(stmt)
    cat = res.scalars().first()
    if not cat:
        cat = Category(name="General", slug="general")
        db.add(cat)
        await db.commit()
        await db.refresh(cat)
    return cat


async def cleanup_test_articles(db: AsyncSession):
    # Delete any existing test articles
    stmt = select(ProcessedArticle).where(ProcessedArticle.slug.like("test-ranking-%"))
    res = await db.execute(stmt)
    articles = res.scalars().all()
    for art in articles:
        await db.delete(art)
    await db.commit()


async def test_1_impact_vs_freshness(db: AsyncSession, cat: Category):
    logger.info("\n--- Running Test 1: High Impact Old vs Low Impact New ---")
    now = datetime.now(timezone.utc)

    # 1. High Impact Old Article (Age: 18h, Impact: 95)
    pub_at_old = now - timedelta(hours=18)
    # final_score = 95 * 0.60 + 20 * 0.25 + 50 * 0.15 = 57 + 5 + 7.5 = 69.5
    art_old = ProcessedArticle(
        title="OpenAI GPT-6 Major Release and AI Regulation Merger",
        slug="test-ranking-high-impact-old",
        summary="Old but high impact",
        content="OpenAI GPT-6 is a major AI model release.",
        source="System Ingest",
        category_id=cat.id,
        published_status="published",
        published_at=pub_at_old,
        expires_at=pub_at_old + timedelta(hours=24),
        impact_score=95.0,
        freshness_score=20.0,
        engagement_score=50.0,
        final_score=69.5,
        is_archived=False,
    )

    # 2. Low Impact New Article (Age: 1h, Impact: 25)
    pub_at_new = now - timedelta(hours=1)
    # final_score = 25 * 0.60 + 100 * 0.25 + 50 * 0.15 = 15 + 25 + 7.5 = 47.5
    art_new = ProcessedArticle(
        title="Minor blog post product update",
        slug="test-ranking-low-impact-new",
        summary="New but low impact",
        content="This is a minor blog post product update.",
        source="System Ingest",
        category_id=cat.id,
        published_status="published",
        published_at=pub_at_new,
        expires_at=pub_at_new + timedelta(hours=24),
        impact_score=25.0,
        freshness_score=100.0,
        engagement_score=50.0,
        final_score=47.5,
        is_archived=False,
    )

    db.add(art_old)
    db.add(art_new)
    await db.commit()

    # Verify rankings
    homepage_articles = await get_ranked_homepage_articles(db, limit=50)
    # Filter for our test articles
    test_ranked = [a for a in homepage_articles if a.slug.startswith("test-ranking-")]

    assert len(test_ranked) >= 2, f"Expected at least 2 test articles, got {len(test_ranked)}"

    first = test_ranked[0]
    second = test_ranked[1]

    logger.info(f"First ranked test article: {first.title} (Slug: {first.slug}, Final Score: {first.final_score:.2f})")
    logger.info(
        f"Second ranked test article: {second.title} (Slug: {second.slug}, Final Score: {second.final_score:.2f})"
    )

    assert first.slug == "test-ranking-high-impact-old", "Expected High Impact Old to rank above Low Impact New"
    logger.info("Test 1 SUCCESSFUL: High Impact Old Article ranks above Low Impact New Article.")


async def test_2_hard_expiry(db: AsyncSession, cat: Category):
    logger.info("\n--- Running Test 2: 24-Hour Hard Expiry ---")
    now = datetime.now(timezone.utc)

    # Article older than 24 hours
    pub_at_expired = now - timedelta(hours=24, minutes=1)
    art_expired = ProcessedArticle(
        title="Very Old Expired Article",
        slug="test-ranking-expired",
        summary="Expired",
        content="Very old expired article content.",
        source="System Ingest",
        category_id=cat.id,
        published_status="published",
        published_at=pub_at_expired,
        expires_at=pub_at_expired + timedelta(hours=24),
        impact_score=90.0,
        freshness_score=0.0,
        engagement_score=50.0,
        final_score=61.5,
        is_archived=False,
    )

    db.add(art_expired)
    await db.commit()

    # Run the expiry logic
    archived_count = await expire_old_articles(db)
    logger.info(f"Archived {archived_count} expired article(s).")

    # Fetch article from DB to verify it's marked archived
    stmt = select(ProcessedArticle).where(ProcessedArticle.slug == "test-ranking-expired")
    res = await db.execute(stmt)
    art = res.scalars().first()

    assert art.is_archived is True, "Expected article is_archived to be True"
    assert art.published_status == "archived", "Expected article published_status to be 'archived'"

    # Check if it appears in homepage rankings
    homepage_articles = await get_ranked_homepage_articles(db, limit=10)
    assert not any(a.slug == "test-ranking-expired" for a in homepage_articles), (
        "Expired article should NOT be in homepage feed"
    )

    logger.info("Test 2 SUCCESSFUL: Old article archived and removed from homepage.")


async def test_3_feed_composition(db: AsyncSession, cat: Category):
    logger.info("\n--- Running Test 3: 70% Current / 30% Previous Feed Composition ---")
    now = datetime.now(timezone.utc)

    # Clear test articles first to have an exact count
    await cleanup_test_articles(db)

    # Create 10 Current Articles (Age: 3 hours)
    for i in range(10):
        pub_at = now - timedelta(hours=3)
        art = ProcessedArticle(
            title=f"Current Article {i}",
            slug=f"test-ranking-current-{i}",
            summary="Current window",
            content="Content",
            source="System Ingest",
            category_id=cat.id,
            published_status="published",
            published_at=pub_at,
            expires_at=pub_at + timedelta(hours=24),
            impact_score=1000.0,
            freshness_score=1000.0,
            engagement_score=1000.0,
            final_score=1000.0,
            is_archived=False,
        )
        db.add(art)

    # Create 10 Previous Articles (Age: 18 hours)
    for i in range(10):
        pub_at = now - timedelta(hours=18)
        art = ProcessedArticle(
            title=f"Previous Article {i}",
            slug=f"test-ranking-prev-{i}",
            summary="Previous window",
            content="Content",
            source="System Ingest",
            category_id=cat.id,
            published_status="published",
            published_at=pub_at,
            expires_at=pub_at + timedelta(hours=24),
            impact_score=999.0,  # Higher impact but older
            freshness_score=999.0,
            engagement_score=999.0,
            final_score=999.0,
            is_archived=False,
        )
        db.add(art)

    await db.commit()

    # Query 10 ranked articles
    limit = 10
    homepage_articles = await get_ranked_homepage_articles(db, limit=limit)

    current_count = 0
    prev_count = 0

    for art in homepage_articles:
        if "test-ranking-current-" in art.slug:
            current_count += 1
        elif "test-ranking-prev-" in art.slug:
            prev_count += 1

    logger.info(f"Feed composition with limit={limit}:")
    logger.info(f" - Current window articles (0-12h): {current_count} (Expected: 7)")
    logger.info(f" - Previous window articles (12-24h): {prev_count} (Expected: 3)")

    assert current_count == 7, f"Expected 7 current articles, got {current_count}"
    assert prev_count == 3, f"Expected 3 previous articles, got {prev_count}"
    logger.info("Test 3 SUCCESSFUL: Feed contains exactly 70% Current and 30% Previous articles.")


async def test_4_manual_ranking_run(db: AsyncSession, cat: Category):
    logger.info("\n--- Running Test 4: Manual Ranking Run & Score Population ---")

    # Ensure some active test articles exist
    now = datetime.now(timezone.utc)
    pub_at = now - timedelta(hours=4)
    art = ProcessedArticle(
        title="OpenAI GPT-6 model release announced by nvidia regulatory body",
        slug="test-ranking-active-to-score",
        summary="To be scored",
        content="This is active content.",
        source="System Ingest",
        category_id=cat.id,
        published_status="published",
        published_at=pub_at,
        expires_at=pub_at + timedelta(hours=24),
        impact_score=0.0,
        freshness_score=0.0,
        engagement_score=0.0,
        final_score=0.0,
        is_archived=False,
    )
    db.add(art)
    await db.commit()

    # Run the rank_articles task manually
    metrics = await rank_articles(db)
    logger.info(f"Rank articles metrics: {metrics}")

    # Retrieve our article
    stmt = select(ProcessedArticle).where(ProcessedArticle.slug == "test-ranking-active-to-score")
    res = await db.execute(stmt)
    scored_art = res.scalars().first()

    logger.info(f"Calculated scores for '{scored_art.title}':")
    logger.info(f" - Impact Score: {scored_art.impact_score}")
    logger.info(f" - Freshness Score: {scored_art.freshness_score}")
    logger.info(f" - Engagement Score: {scored_art.engagement_score}")
    logger.info(f" - Final Score: {scored_art.final_score}")

    assert scored_art.impact_score > 0, "Impact score should be populated"
    assert scored_art.freshness_score > 0, "Freshness score should be populated"
    assert scored_art.final_score > 0, "Final score should be populated"

    # Verify Redis metrics cache
    redis_c = get_redis_client()
    cached = await redis_c.get("ranking_engine_metrics")
    assert cached is not None, "Expected ranking_engine_metrics in Redis cache"
    cached_data = json.loads(cached)
    logger.info(f"Cached metrics: {cached_data}")

    # Verify audit log exists
    from app.models.user import AuditLog

    audit_stmt = select(AuditLog).where(AuditLog.action == "RANKING_RUN").order_by(AuditLog.id.desc()).limit(1)
    audit_res = await db.execute(audit_stmt)
    audit_event = audit_res.scalars().first()

    assert audit_event is not None, "Expected RANKING_RUN audit log to be created"
    logger.info(f"Audit log metadata: {audit_event.metadata_}")

    logger.info("Test 4 SUCCESSFUL: Manual ranking runs, calculates all scores, updates Redis, and logs audit event.")


async def main():
    async with AsyncSessionLocal() as db:
        cat = await get_or_create_category(db)
        await cleanup_test_articles(db)
        try:
            await test_1_impact_vs_freshness(db, cat)
            await test_2_hard_expiry(db, cat)
            await test_3_feed_composition(db, cat)
            await test_4_manual_ranking_run(db, cat)
            logger.info("\n========================================================")
            logger.info("ALL NEWS RANKING ENGINE TESTS PASSED SUCCESSFULLY!")
            logger.info("========================================================")
        finally:
            await cleanup_test_articles(db)


if __name__ == "__main__":
    asyncio.run(main())
