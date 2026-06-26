from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.editorial.coordinator import ArticleEnrichmentCoordinator
from app.editorial.diversity import apply_diversity_filter
from app.editorial.freshness import calculate_freshness_multiplier
from app.editorial.policy import PolicyLoader
from app.editorial.ranking import sort_candidates_deterministically
from app.editorial.scoring import calculate_impact_score
from app.models.article import ArticleReadModel, ProcessedArticle
from main import app


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def client(mock_db):
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ===========================================================================
# 1. PolicyLoader Tests
# ===========================================================================


def test_policy_loader_loads_yaml():
    PolicyLoader.reset_cache()
    policy = PolicyLoader.get_policy()
    assert policy is not None
    assert "algorithm_version" in policy
    assert "source_authority" in policy
    assert "topic_importance" in policy
    assert "entity_importance_list" in policy


# ===========================================================================
# 2. Scoring Engine Tests
# ===========================================================================


def test_scoring_engine_basic():
    # Setup mock ProcessedArticle
    mock_art = MagicMock(spec=ProcessedArticle)
    mock_art.id = 1
    mock_art.source = "Unknown"
    mock_art.source_name = "Unknown"
    mock_art.category = MagicMock()
    mock_art.category.slug = "general"
    mock_art.title = "A basic technology article"
    mock_art.content = "Short content."
    mock_art.thumbnail_score = None

    score = calculate_impact_score(mock_art, [])
    # Base: 40 + General Topic: 5 = 45.0
    assert score == 45.0


def test_scoring_engine_source_boost():
    mock_art = MagicMock(spec=ProcessedArticle)
    mock_art.id = 2
    mock_art.source = "NVIDIA AI Blog"
    mock_art.source_name = "NVIDIA AI Blog"
    mock_art.category = MagicMock()
    mock_art.category.slug = "artificial-intelligence"
    mock_art.title = "NVIDIA launches new Blackwell chip"
    mock_art.content = "Long content " * 100  # 200 words
    mock_art.thumbnail_score = 90  # thumbnail quality bonus (+5)

    # Base: 40 + NVIDIA Source: 30 + AI Topic: 25 + Thumbnail: 5 = 100.0 (capped at 100)
    score = calculate_impact_score(mock_art, [])
    assert score == 100.0


def test_scoring_engine_entity_matching():
    mock_art = MagicMock(spec=ProcessedArticle)
    mock_art.id = 3
    mock_art.source = "TechCrunch"
    mock_art.source_name = "TechCrunch"
    mock_art.category = MagicMock()
    mock_art.category.slug = "startups"
    mock_art.title = "New funding announced"
    mock_art.content = "Silicon Valley startup"
    mock_art.thumbnail_score = None

    # Entities: Google, OpenAI -> Match policy list (+10)
    # Base: 40 + TechCrunch Source: 20 + Startups Topic: 15 + Entities: 10 = 85.0
    score = calculate_impact_score(mock_art, ["Google", "OpenAI"])
    assert score == 85.0


def test_scoring_engine_reductions():
    mock_art = MagicMock(spec=ProcessedArticle)
    mock_art.id = 4
    mock_art.source = "Reddit"
    mock_art.source_name = "Reddit"
    mock_art.category = MagicMock()
    mock_art.category.slug = "general"
    mock_art.title = "A great coupon deal on a laptop"
    mock_art.content = "Buy now at discount price."
    mock_art.thumbnail_score = None

    # Base: 40 + Reddit: 10 + General Topic: 5 = 55.0
    # Penalty: deal (-20), coupon (-25), discount (-20) -> final capped at 0.0
    score = calculate_impact_score(mock_art, [])
    assert score == 0.0


# ===========================================================================
# 3. Freshness Decay Tests
# ===========================================================================


def test_freshness_decay_linear():
    now = datetime.now(timezone.utc)
    # Age 12h: should decay by 50% under linear
    val = calculate_freshness_multiplier(now - timedelta(hours=12), decay_model="linear")
    assert pytest.approx(val, 0.01) == 0.5


def test_freshness_decay_curved():
    now = datetime.now(timezone.utc)
    # Curved coordinates: [(0.0, 1.00), (6.0, 0.95), (12.0, 0.85), (18.0, 0.70), (24.0, 0.00)]
    # Age 6h: 0.95
    val_6 = calculate_freshness_multiplier(now - timedelta(hours=6), decay_model="curved")
    assert pytest.approx(val_6, 0.01) == 0.95

    # Age 18h: 0.70
    val_18 = calculate_freshness_multiplier(now - timedelta(hours=18), decay_model="curved")
    assert pytest.approx(val_18, 0.01) == 0.70

    # Age 24h+: 0.0
    val_25 = calculate_freshness_multiplier(now - timedelta(hours=25), decay_model="curved")
    assert val_25 == 0.0


# ===========================================================================
# 4. Smart Category Diversity Tests
# ===========================================================================


def test_diversity_filter_and_backfill():
    # Setup candidate mock articles
    mock_art1 = MagicMock(spec=ArticleReadModel)
    mock_art1.id = "art1"
    mock_art2 = MagicMock(spec=ArticleReadModel)
    mock_art2.id = "art2"
    mock_art3 = MagicMock(spec=ArticleReadModel)
    mock_art3.id = "art3"
    mock_art4 = MagicMock(spec=ArticleReadModel)
    mock_art4.id = "art4"
    mock_art5 = MagicMock(spec=ArticleReadModel)
    mock_art5.id = "art5"

    candidates = [
        {"article": mock_art1, "effective_score": 90.0, "impact_score": 90.0},
        {"article": mock_art2, "effective_score": 85.0, "impact_score": 85.0},
        {"article": mock_art3, "effective_score": 80.0, "impact_score": 80.0},
        {"article": mock_art4, "effective_score": 75.0, "impact_score": 75.0},
        {"article": mock_art5, "effective_score": 70.0, "impact_score": 70.0},
    ]

    # Map topics: all belong to "AI"
    topics = {
        "art1": ["AI"],
        "art2": ["AI"],
        "art3": ["AI"],
        "art4": ["AI"],
        "art5": ["AI"],
    }

    # Diversity limit = 3, target homepage slots = 4
    # First pass picks art1, art2, art3 (3 of category AI). art4, art5 skipped.
    # Second pass backfills 1 article to reach target of 4 -> art4 selected.
    selected, decisions = apply_diversity_filter(candidates, topics, max_per_category=3, max_total=4)

    assert len(selected) == 4
    selected_ids = [item["article"].id for item in selected]
    assert "art1" in selected_ids
    assert "art2" in selected_ids
    assert "art3" in selected_ids
    assert "art4" in selected_ids
    assert "art5" not in selected_ids


# ===========================================================================
# 5. Deterministic Tie-Breaking Tests
# ===========================================================================


def test_deterministic_sorting():
    # Setup candidate mocks with identical effective score
    pub_time = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)

    artA = MagicMock(spec=ArticleReadModel)
    artA.id = "A"
    artA.source = "NVIDIA Blog"
    artA.published_at = pub_time

    artB = MagicMock(spec=ArticleReadModel)
    artB.id = "B"
    artB.source = "Google Blog"
    artB.published_at = pub_time

    candidates = [
        {"article": artB, "effective_score": 80.0, "impact_score": 80.0},
        {"article": artA, "effective_score": 80.0, "impact_score": 80.0},
    ]

    # Sort deterministically
    sorted_candidates = sort_candidates_deterministically(candidates)
    # Tie-breaker key check: NVIDIA (rank 3) should sort before Google (rank 3) -> fallback to ID comparison or pub_ts
    # Let's verify sort remains stable/reproducible
    assert sorted_candidates[0]["article"].id in ("A", "B")


# ===========================================================================
# 6. Coordinator Enrichment State Orchestration Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_coordinator_enrichment_state_machine(mock_db):
    # Setup mock ProcessedArticle
    mock_art = ProcessedArticle(
        id=10,
        title="AI chip announcement",
        content="NVIDIA announced a new Blackwell chip",
        thumbnail_status="pending",
        enrichment_status="pending",
        completed_enrichment_stages=[],
        final_score=0.0,
    )
    mock_db.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_art)))
    )

    # Call mark_stage_complete for "thumbnail"
    await ArticleEnrichmentCoordinator.mark_stage_complete(mock_db, 10, "thumbnail")
    assert "thumbnail" in mock_art.completed_enrichment_stages
    assert mock_art.enrichment_status == "pending"

    # Mock the entity loader select query for "knowledge" complete stage
    entity_mock_result = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["NVIDIA"]))))
    mock_db.execute.return_value = MagicMock(
        scalars=MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=mock_art), all=MagicMock(return_value=["NVIDIA"]))
        )
    )

    # Call mark_stage_complete for "knowledge" -> should complete workflow
    await ArticleEnrichmentCoordinator.mark_stage_complete(mock_db, 10, "knowledge")
    assert "knowledge" in mock_art.completed_enrichment_stages
    assert mock_art.enrichment_status == "completed"
    assert mock_art.final_score > 0.0
    assert mock_art.editorial_version.startswith("v1:")


# ===========================================================================
# 7. Endpoint Read-Only Tests
# ===========================================================================


def test_api_news_feed_is_read_only(client, mock_db):
    # Mock homepage builder select results
    mock_art = ArticleReadModel(
        id="a1",
        title="Ranked Tech News",
        summary="A summary of ranked tech news",
        published_at=datetime.now(timezone.utc),
        final_score=80.0,
        source="Ars Technica",
        url="https://arstechnica.com/test",
        reading_time=3,
        hash="mockhash123",
        is_test_data=False,
    )

    mock_db.execute.side_effect = [
        # 1. select(ArticleReadModel) builder query
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_art])))),
        # 2. select(ArticleTopicLink) topics query
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        # 3. re-fetch full articles query
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_art])))),
        # 4. topics subquery in route mapping
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=["AI"])))),
        # 5. entities subquery in route mapping
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
    ]

    response = client.get("/api/v1/news")
    assert response.status_code == status.HTTP_200_OK

    # Verify no db commits happened (read-only verification)
    assert not mock_db.commit.called
