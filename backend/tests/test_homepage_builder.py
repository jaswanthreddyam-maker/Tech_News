import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from app.editorial.homepage_builder import HomepageBuilder
from app.models.article import ArticleReadModel

@pytest.mark.asyncio
async def test_homepage_builder_final_score_included(db_session, clean_db_tables):
    # Test 1: final_score = 80 -> Included
    article = ArticleReadModel(
        id="test-high-impact",
        url="https://test.com/high-impact",
        title="High Impact Article",
        content="Content",
        published_at=datetime.now(timezone.utc) - timedelta(hours=2),
        final_score=80.0,
        published_status="published",
        source="Test Source",
        hash="test-hash",
        is_test_data=False
    )
    db_session.add(article)
    await db_session.commit()
    
    results = await HomepageBuilder.build_homepage(db_session)
    assert any(a.id == "test-high-impact" for a in results), "High impact article should be included"

@pytest.mark.asyncio
async def test_homepage_builder_final_score_zero_filtered(db_session, clean_db_tables):
    # Test 2: final_score = 0 -> Filtered
    article_zero = ArticleReadModel(
        id="test-zero-impact",
        url="https://test.com/zero-impact",
        title="Zero Impact Article",
        content="Content",
        published_at=datetime.now(timezone.utc) - timedelta(hours=2),
        final_score=0.0,
        published_status="published",
        source="Test Source",
        hash="test-hash-zero",
        is_test_data=False
    )
    article_high = ArticleReadModel(
        id="test-high-impact-dummy",
        url="https://test.com/high-impact-dummy",
        title="High Impact Article Dummy",
        content="Content",
        published_at=datetime.now(timezone.utc) - timedelta(hours=2),
        final_score=80.0,
        published_status="published",
        source="Test Source",
        hash="test-hash-high",
        is_test_data=False
    )
    db_session.add(article_zero)
    db_session.add(article_high)
    await db_session.commit()
    
    results = await HomepageBuilder.build_homepage(db_session)
    assert not any(a.id == "test-zero-impact" for a in results), "Zero impact article should be filtered"
    assert any(a.id == "test-high-impact-dummy" for a in results), "High impact article should be included"

@pytest.mark.asyncio
async def test_homepage_builder_fresh_article_included(db_session, clean_db_tables):
    # Test 3: Fresh article -> Included
    article = ArticleReadModel(
        id="test-fresh-impact",
        url="https://test.com/fresh-impact",
        title="Fresh Article",
        content="Content",
        published_at=datetime.now(timezone.utc),
        final_score=80.0,
        published_status="published",
        source="Test Source",
        hash="test-hash",
        is_test_data=False
    )
    db_session.add(article)
    await db_session.commit()
    
    results = await HomepageBuilder.build_homepage(db_session)
    assert any(a.id == "test-fresh-impact" for a in results), "Fresh high-impact article should be included"

@pytest.mark.asyncio
async def test_homepage_builder_old_article_filtered(db_session, clean_db_tables):
    # Test 4: Old article -> Filtered due to freshness multiplier
    article = ArticleReadModel(
        id="test-old-impact",
        url="https://test.com/old-impact",
        title="Old Article",
        content="Content",
        published_at=datetime.now(timezone.utc) - timedelta(hours=36),
        final_score=100.0,
        published_status="published",
        source="Test Source",
        hash="test-hash",
        is_test_data=False
    )
    db_session.add(article)
    await db_session.commit()
    
    results = await HomepageBuilder.build_homepage(db_session)
    assert not any(a.id == "test-old-impact" for a in results), "36-hour old article should be filtered"

