import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.editorial.homepage_builder import HomepageBuilder
from app.models.article import ArticleReadModel, Category, ProcessedArticle
from app.services.ingestion.replenishment import AutoReplenishmentService
from app.services.ranking.news_ranking_engine import expire_articles


@pytest.mark.asyncio
async def test_expire_articles_expires_week_old_articles(db_session):
    """
    Verifies that articles older than 48h (e.g. 7 days old) are strictly expired
    and not extended indefinitely by circuit breakers.
    """
    cat = await db_session.scalar(select(Category).limit(1))
    if not cat:
        cat = Category(name="Artificial Intelligence", slug="artificial-intelligence")
        db_session.add(cat)
        await db_session.flush()

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Insert a 7-day-old article that reached its expiration date
    proc_old = ProcessedArticle(
        id=9901,
        title="Week Old Breakthrough In Tech",
        slug="week-old-breakthrough-in-tech",
        summary="This was news a week ago.",
        content="Detailed content from last week.",
        source="Tech Daily",
        source_name="Tech Daily",
        category_id=cat.id,
        published_status="published",
        published_at=week_ago,
        expires_at=week_ago + timedelta(hours=24),  # Expired 6 days ago
        is_expired=False,
        is_archived=False,
        is_test_data=False,
    )
    db_session.add(proc_old)
    await db_session.commit()

    # Run expiration engine
    metrics = await expire_articles(db_session)

    # Re-fetch article
    updated = await db_session.get(ProcessedArticle, 9901)
    assert updated.is_expired is True, "Week-old article must be marked is_expired=True"
    assert metrics["expired_articles_total"] >= 1


@pytest.mark.asyncio
async def test_auto_replenishment_debounce(db_session):
    """
    Verifies that AutoReplenishmentService enforces debounce cooldown
    and does not trigger duplicate parallel crawls.
    """
    # 1. Reset cooldown
    await AutoReplenishmentService.set_cooldown(60)

    # 2. First check should report cooldown active
    res1 = await AutoReplenishmentService.trigger_replenishment_if_needed(db_session, force=False)
    assert res1["triggered"] is False
    assert res1["reason"] == "COOLDOWN_ACTIVE"


@pytest.mark.asyncio
async def test_homepage_builder_replaces_expired_with_fresh(db_session):
    """
    Verifies that HomepageBuilder only selects active, unexpired articles
    and rejects 7-day-old expired articles.
    """
    cat = await db_session.scalar(select(Category).limit(1))
    if not cat:
        cat = Category(name="Artificial Intelligence", slug="artificial-intelligence")
        db_session.add(cat)
        await db_session.flush()

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # 1. Expired week-old article in ProcessedArticle and ArticleReadModel
    proc_expired = ProcessedArticle(
        id=9902,
        title="Expired News From 7 Days Ago",
        slug="expired-news-7-days-ago",
        summary="Old summary.",
        content="Old content.",
        source="Old Publisher",
        category_id=cat.id,
        published_status="published",
        published_at=week_ago,
        expires_at=week_ago + timedelta(hours=24),
        is_expired=True,
        is_archived=False,
        is_test_data=False,
    )
    read_expired = ArticleReadModel(
        id="9902",
        url="https://news.com/expired",
        title="Expired News From 7 Days Ago",
        content="Old content.",
        published_at=week_ago,
        publication_status="PUBLISHED",
        published_status="published",
        source="Old Publisher",
        hash="hash_old",
        is_test_data=False,
        final_score=85.0,
    )

    # 2. Fresh new article (< 1 hour old)
    proc_fresh = ProcessedArticle(
        id=9903,
        title="Fresh Breaking AI Announcement",
        slug="fresh-breaking-ai-announcement",
        summary="New summary just published.",
        content="Fresh content just released.",
        source="AI Today",
        category_id=cat.id,
        published_status="published",
        published_at=now - timedelta(minutes=30),
        expires_at=now + timedelta(hours=24),
        is_expired=False,
        is_archived=False,
        is_test_data=False,
    )
    read_fresh = ArticleReadModel(
        id="9903",
        url="https://news.com/fresh",
        title="Fresh Breaking AI Announcement",
        content="Fresh content just released.",
        published_at=now - timedelta(minutes=30),
        publication_status="PUBLISHED",
        published_status="published",
        source="AI Today",
        hash="hash_fresh",
        is_test_data=False,
        final_score=90.0,
    )

    db_session.add_all([proc_expired, read_expired, proc_fresh, read_fresh])
    await db_session.commit()

    # Build homepage
    articles = await HomepageBuilder.build_homepage(db_session)

    article_ids = [a.id for a in articles]
    assert "9903" in article_ids, "Fresh article should be on homepage"
    assert "9902" not in article_ids, "Expired 7-day-old article must NOT be on homepage"
