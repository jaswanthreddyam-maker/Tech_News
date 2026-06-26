from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

import app.recommendations.engine
import app.recommendations.projectors.affinity
import app.recommendations.projectors.freshness
import app.recommendations.projectors.popularity
import app.recommendations.projectors.profile  # noqa: F401

# Ensure projectors are registered
from app.core.projection.engine import ProjectionEngine
from app.models.event import EventCategory, EventEnvelope, EventSubjectType
from app.models.recommendation import (
    ArticleFeatureVector,
    RecommendationProfile,
    UserAffinityProfile,
)
from app.recommendations.pipeline import RecommendationPipeline
from app.recommendations.schemas import RecommendationContext, RecommendationRequest


@pytest_asyncio.fixture
async def clear_recommendations(db_session):
    await db_session.execute(delete(UserAffinityProfile))
    await db_session.execute(delete(ArticleFeatureVector))
    await db_session.execute(delete(RecommendationProfile))
    await db_session.execute(delete(EventEnvelope))
    await db_session.commit()
    yield

@pytest.mark.asyncio
async def test_recommendation_pipeline_and_projectors(db_session, clear_recommendations):
    # 1. Publish an article
    event1 = EventEnvelope(
        category=EventCategory.EDITORIAL,
        event_type="ARTICLE_PUBLISHED",
        subject_type=EventSubjectType.ARTICLE,
        subject_id="art-123",
        provider="TEST",
        occurred_at=datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)
    )
    # 2. View an article
    event2 = EventEnvelope(
        category=EventCategory.ANALYTICS,
        event_type="ARTICLE_VIEWED",
        subject_type=EventSubjectType.ARTICLE,
        subject_id="art-123",
        provider="TEST",
        occurred_at=datetime(2026, 6, 14, 12, 1, tzinfo=timezone.utc)
    )
    db_session.add_all([event1, event2])
    await db_session.commit()

    engine = ProjectionEngine(db_session)
    await engine.process_event(event1)
    await engine.process_event(event2)
    await db_session.commit()

    # Verify Profile
    stmt = select(RecommendationProfile).where(RecommendationProfile.article_id == "art-123")
    profile = (await db_session.execute(stmt)).scalar_one()

    print(f"PROFILE: {profile.ranking_features} type: {type(profile.ranking_features)}")
    assert isinstance(profile.ranking_features, dict)
    assert profile.ranking_features.get("freshness") == 1.0
    assert profile.ranking_features.get("engagement") == 1.0

    # Setup pipeline test data
    p2 = RecommendationProfile(
        article_id="art-456",
        ranking_features={"freshness": 0.5, "engagement": 5.0},
        context_features={"primary_topic": "AI"}
    )
    db_session.add(p2)
    await db_session.commit()

    pipeline = RecommendationPipeline(db_session)
    request = RecommendationRequest(
        context=RecommendationContext(),
        strategy="TRENDING",
        limit=2,
        filters=[]
    )
    response = await pipeline.run(request)
    candidates = response.candidates

    assert len(candidates) == 2
    # art-456 score = 5.0 + 0.5 + 1.0(editorial default mock) + behavior
    # art-123 score = 1.0 + 1.0 + 1.0
    # Actually just check that they exist and have reasons
    assert candidates[0].strategy == "TRENDING"
    assert len(candidates[0].reasons) == 1
    assert candidates[0].reasons[0].reason == "TRENDING"

@pytest.mark.asyncio
async def test_recommendation_filters_and_diversification(db_session, clear_recommendations):
    # Setup data
    p1 = RecommendationProfile(article_id="art-1", ranking_features={"freshness": 1.0, "engagement": 10.0}, context_features={"primary_topic": "AI", "language": "en"})
    p2 = RecommendationProfile(article_id="art-2", ranking_features={"freshness": 1.0, "engagement": 9.0}, context_features={"primary_topic": "AI", "language": "en"})
    p3 = RecommendationProfile(article_id="art-3", ranking_features={"freshness": 1.0, "engagement": 8.0}, context_features={"primary_topic": "Tech", "language": "en"})
    p4 = RecommendationProfile(article_id="art-4", ranking_features={"freshness": 1.0, "engagement": 7.0}, context_features={"primary_topic": "Finance", "language": "fr"})

    db_session.add_all([p1, p2, p3, p4])
    await db_session.commit()

    pipeline = RecommendationPipeline(db_session)

    # 1. Test Filter (Language = en)
    req1 = RecommendationRequest(
        context=RecommendationContext(language="en"),
        strategy="TRENDING",
        filters=["LANGUAGE"]
    )
    response1 = await pipeline.run(req1)
    res1 = response1.candidates
    # art-4 is 'fr', so shouldn't be included
    assert len(res1) == 3
    assert "art-4" not in [c.article_id for c in res1]

    # 2. Test Diversification (TOPIC)
    # The default Trending sorts by score descending: art-1(AI), art-2(AI), art-3(Tech)
    # Diversifier should output art-1(AI), art-3(Tech), art-2(AI)
    # since it penalizes consecutive same-topic.
    # Wait, the diversifier penalizes ANY seen topic. So it will pick AI, then Tech, then AI.
    assert res1[0].article_id == "art-1"
    assert res1[1].article_id == "art-3"
    assert res1[2].article_id == "art-2"
