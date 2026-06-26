import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.article import ProcessedArticle
from app.models.source import Source
from main import app

# ---------------------------------------------------------------------------
# API Contract Tests Setup
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def client(mock_db):
    # Override FastAPI dependency for database session
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test Endpoint: GET /api/v1/telemetry
# ---------------------------------------------------------------------------


def test_get_dashboard_telemetry_schema(client, mock_db):
    # Setup sequential execute mocks for the multiple telemetry SQL queries
    mock_execute_returns = [
        # 1. Ingestion rate check query (rate_stmt)
        MagicMock(scalar=MagicMock(return_value=6)),
        # 2. Raw article lifecycle states query (raw_stmt)
        MagicMock(all=MagicMock(return_value=[("fetched", 5), ("processed", 12)])),
        # 3. Raw 24h count (raw_stmt_24)
        MagicMock(all=MagicMock(return_value=[("fetched", 2), ("processed", 5)])),
        # 4. Processed article count query (proc_stmt)
        MagicMock(all=MagicMock(return_value=[("published", 12)])),
        # 5. Processed 24h count (proc_stmt_24)
        MagicMock(all=MagicMock(return_value=[("published", 6)])),
        # 6. Processed total query (total_stmt)
        MagicMock(scalar=MagicMock(return_value=12)),
        # 7. Thumbnail downloaded count (dl_stmt)
        MagicMock(scalar=MagicMock(return_value=9)),
        # 8. Thumbnail fallback usage (fb_stmt)
        MagicMock(scalar=MagicMock(return_value=2)),
        # 9. Thumbnail source distribution query (dist_stmt)
        MagicMock(all=MagicMock(return_value=[("techcrunch", 9)])),
    ]
    mock_db.execute.side_effect = mock_execute_returns

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.llen.return_value = 4
    mock_redis.keys.return_value = [b"active_crawl:1", b"active_crawl:2"]
    mock_redis.get.return_value = json.dumps(
        {
            "articles_evaluated": 150,
            "active_articles": 45,
            "expired_articles": 105,
            "avg_impact_score": 75.2,
            "avg_final_score": 82.5,
            "last_run": "2026-06-09T12:00:00Z",
            "next_run": "2026-06-09T13:00:00Z",
        }
    ).encode("utf-8")

    with patch("app.api.v1.routes.telemetry.get_redis_client", return_value=mock_redis):
        response = client.get("/api/v1/telemetry")

    assert response.status_code == status.HTTP_200_OK

    payload = response.json()
    assert "correlation_id" in payload
    assert "data" in payload

    data = payload["data"]
    # Check current state (V3 structure)
    assert data["current_state"]["queue_depth"]["value"] == 4
    assert data["current_state"]["active_crawlers"]["value"] == 2

    # Check throughput
    assert data["throughput"]["ingestion_rate_sec"]["value"] == 0.1  # 6 articles / 60 seconds

    # Check historical
    assert data["historical"]["all_time"]["fetched"] == 5
    assert data["historical"]["all_time"]["processed"] == 12
    assert data["historical"]["all_time"]["published"] == 12

    # Check quality
    assert data["quality"]["thumbnail_coverage"]["value"] == 75.0  # 9 / 12 * 100

    # Check ranking engine
    assert data["ranking_engine"]["articles_evaluated"]["value"] == 150
    assert data["quality"]["average_ranking_score"]["value"] == 82.5


# ---------------------------------------------------------------------------
# Test Endpoint: GET /api/v1/telemetry/sources
# ---------------------------------------------------------------------------


def test_get_sources_telemetry_contract(client, mock_db):
    # Setup mock sources list using actual Source objects
    mock_source1 = Source(
        id=1,
        name="Source A",
        url="http://a.com",
        category="official",
        method="rss",
        enabled=True,
        health_state="healthy",
        credibility_score=95,
        reliability_score=100.0,
        total_crawls=10,
        successful_crawls=10,
        failure_count=0,
        last_crawl_at=datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc),
        last_failure_type=None,
    )
    mock_source2 = Source(
        id=2,
        name="Source B",
        url="http://b.com",
        category="editorial",
        method="rss",
        enabled=False,
        health_state="offline",
        credibility_score=75,
        reliability_score=80.0,
        total_crawls=5,
        successful_crawls=4,
        failure_count=1,
        last_crawl_at=None,
        last_failure_type="timeout",
    )

    # Sequential db execute calls:
    # 1. select(Source).order_by(Source.name)
    # 2. select(RawArticle.article_metadata) for Source A
    # 3. select(RawArticle.article_metadata) for Source B
    mock_db.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_source1, mock_source2])))),
        MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=[json.dumps({"response_time_ms": 320})]))
            )
        ),
        MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        ),  # no recent latency logs for Source B
    ]

    response = client.get("/api/v1/telemetry/sources")
    assert response.status_code == status.HTTP_200_OK

    payload = response.json()
    assert "data" in payload
    sources_data = payload["data"]
    assert len(sources_data) == 2

    assert sources_data[0]["name"] == "Source A"
    assert sources_data[0]["avg_latency_ms"] == 320
    assert sources_data[0]["enabled"] is True

    assert sources_data[1]["name"] == "Source B"
    assert sources_data[1]["avg_latency_ms"] == 350  # Fallback default latency
    assert sources_data[1]["enabled"] is False
    assert sources_data[1]["last_failure_type"] == "timeout"


# ---------------------------------------------------------------------------
# Test Endpoint: GET /api/v1/telemetry/trends/{topic}/explorer
# ---------------------------------------------------------------------------


def test_get_trend_explorer_contract(client, mock_db):
    # Setup mock processed articles and sources matching the tag
    mock_art = ProcessedArticle(
        id=101,
        title="AI Revolution",
        slug="ai-revolution",
        summary="A summary of the AI revolution.",
        source="Ars Technica",
        published_at=datetime(2026, 6, 9, 12, 30, tzinfo=timezone.utc),
        tags="ai, tech",
    )
    mock_source = Source(id=20, name="Ars Technica", category="editorial", credibility_score=90, reliability_score=98.5)

    mock_db.execute.side_effect = [
        # select(ProcessedArticle, Source) query
        MagicMock(all=MagicMock(return_value=[(mock_art, mock_source)]))
    ]

    with patch("app.api.v1.routes.telemetry.datetime") as mock_datetime:
        # Mock current time in route to calculate freshness correctly
        mock_datetime.now.return_value = datetime(2026, 6, 9, 12, 45, tzinfo=timezone.utc)
        response = client.get("/api/v1/telemetry/trends/ai/explorer")

    assert response.status_code == status.HTTP_200_OK

    payload = response.json()
    assert "data" in payload
    data = payload["data"]
    assert data["topic"] == "ai"
    assert "15m elapsed since last signal" in data["freshness"]
    assert data["source_diversity"] == 1
    assert data["velocity"] == "+140% velocity acceleration"  # (1 * 40) + (1 * 35) + 65
    assert len(data["articles"]) == 1
    assert data["articles"][0]["title"] == "AI Revolution"
    assert data["sources"][0]["name"] == "Ars Technica"
    assert data["sources"][0]["authority_weight"] == 1.4  # editorial multiplier
