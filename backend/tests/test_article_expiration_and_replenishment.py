import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from fastapi import Response

from app.editorial.homepage_builder import HomepageBuilder
from app.models.article import ArticleReadModel, Category, ProcessedArticle, RawArticle
from app.services.ingestion.replenishment import AutoReplenishmentService
from app.services.ranking.news_ranking_engine import expire_articles
from app.api.v1.routes.news import list_articles, get_category_desks
from app.services.recommendations.engine import TrendingStrategy, BehavioralStrategy


async def _get_or_create_category(db):
    cat = await db.scalar(select(Category).limit(1))
    if not cat:
        cat = Category(name="Artificial Intelligence", slug="artificial-intelligence")
        db.add(cat)
        await db.flush()
    return cat


@pytest.mark.asyncio
async def test_expire_articles_expires_week_old_articles(db_session):
    """
    Verifies that articles older than 48h (e.g. 7 days old) are strictly expired
    and not extended indefinitely by circuit breakers.
    """
    cat = await _get_or_create_category(db_session)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

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

    metrics = await expire_articles(db_session)

    updated = await db_session.get(ProcessedArticle, 9901)
    assert updated.is_expired is True, "Week-old article must be marked is_expired=True"
    assert metrics["expired_articles_total"] >= 1


@pytest.mark.asyncio
async def test_auto_replenishment_debounce(db_session):
    """
    Verifies that AutoReplenishmentService enforces debounce cooldown
    and does not trigger duplicate parallel crawls.
    """
    await AutoReplenishmentService.set_cooldown(60)

    res1 = await AutoReplenishmentService.trigger_replenishment_if_needed(db_session, force=False)
    assert res1["triggered"] is False
    assert res1["reason"] == "COOLDOWN_ACTIVE"


@pytest.mark.asyncio
async def test_homepage_builder_replaces_expired_with_fresh(db_session):
    """
    Verifies that HomepageBuilder only selects active, unexpired articles
    and rejects 7-day-old expired articles.
    """
    cat = await _get_or_create_category(db_session)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

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

    articles = await HomepageBuilder.build_homepage(db_session)

    article_ids = [a.id for a in articles]
    assert "9903" in article_ids, "Fresh article should be on homepage"
    assert "9902" not in article_ids, "Expired 7-day-old article must NOT be on homepage"


@pytest.mark.asyncio
async def test_news_endpoint_excludes_expired_articles(db_session):
    """
    Verifies that the /api/v1/news route strictly filters out expired articles
    even when sort_by='freshness' is used.
    """
    cat = await _get_or_create_category(db_session)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    proc_expired = ProcessedArticle(
        id=9904,
        title="Expired News From 7 Days Ago",
        slug="expired-news-7-days-ago-route",
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
        id="9904",
        url="https://news.com/expired-route",
        title="Expired News From 7 Days Ago",
        content="Old content.",
        published_at=week_ago,
        publication_status="PUBLISHED",
        published_status="published",
        source="Old Publisher",
        hash="hash_old_route",
        is_test_data=False,
        final_score=80.0,
    )

    proc_fresh = ProcessedArticle(
        id=9905,
        title="Fresh Route News",
        slug="fresh-route-news",
        summary="Fresh summary.",
        content="Fresh content.",
        source="Fresh Daily",
        category_id=cat.id,
        published_status="published",
        published_at=now - timedelta(minutes=10),
        expires_at=now + timedelta(hours=24),
        is_expired=False,
        is_archived=False,
        is_test_data=False,
    )
    read_fresh = ArticleReadModel(
        id="9905",
        url="https://news.com/fresh-route",
        title="Fresh Route News",
        content="Fresh content.",
        published_at=now - timedelta(minutes=10),
        publication_status="PUBLISHED",
        published_status="published",
        source="Fresh Daily",
        hash="hash_fresh_route",
        is_test_data=False,
        final_score=95.0,
    )

    db_session.add_all([proc_expired, read_expired, proc_fresh, read_fresh])
    await db_session.commit()

    resp = Response()
    res = await list_articles(
        response=resp,
        category=None,
        cursor=None,
        sort_by="freshness",
        limit=10,
        db=db_session
    )

    item_ids = [card.id for card in res.data]
    assert "9905" in item_ids, "Fresh article should be present in fresh feed"
    assert "9904" not in item_ids, "Expired article should NOT be present in fresh feed"


@pytest.mark.asyncio
async def test_recommendations_exclude_expired_articles(db_session):
    """
    Verifies that TrendingStrategy filters out expired articles.
    """
    cat = await _get_or_create_category(db_session)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    proc_expired = ProcessedArticle(
        id=9906,
        title="Expired Recommendation",
        slug="expired-rec",
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
    proc_fresh = ProcessedArticle(
        id=9907,
        title="Fresh Recommendation",
        slug="fresh-rec",
        summary="Fresh summary.",
        content="Fresh content.",
        source="Fresh Daily",
        category_id=cat.id,
        published_status="published",
        published_at=now - timedelta(minutes=15),
        expires_at=now + timedelta(hours=24),
        is_expired=False,
        is_archived=False,
        is_test_data=False,
    )

    db_session.add_all([proc_expired, proc_fresh])
    await db_session.commit()

    strategy = TrendingStrategy()
    recs = await strategy.recommend(db_session, user_id=None, anonymous_id="test-anon", limit=10)

    rec_ids = [r.article["id"] for r in recs if isinstance(r.article, dict)]
    assert 9907 in rec_ids, "Fresh article should be recommended"
    assert 9906 not in rec_ids, "Expired article should NOT be recommended"
