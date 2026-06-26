import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from main import app
from app.models.story import StoryDashboardProjection, StoryAssignmentDecision

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_admin_editorial_overview(db_session: AsyncSession, client: TestClient):
    # Setup mock projection
    now = datetime.now(timezone.utc)
    proj1 = StoryDashboardProjection(
        story_id="proj-1",
        title="Active Story",
        status="ACTIVE",
        editorial_status="DRAFT",
        publication_status="PUBLISHED",
        unique_readers=1000,
        views=2000,
        last_activity_at=now
    )
    proj2 = StoryDashboardProjection(
        story_id="proj-2",
        title="Review Story",
        status="ACTIVE",
        editorial_status="REVIEW",
        publication_status="DRAFT",
        unique_readers=500,
        views=1000,
        last_activity_at=now
    )
    db_session.add_all([proj1, proj2])
    await db_session.commit()

    response = client.get("/api/v1/admin/editorial/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["active_stories"] >= 2
    assert data["needs_review"] >= 1

@pytest.mark.asyncio
async def test_admin_editorial_top_stories(db_session: AsyncSession, client: TestClient):
    response = client.get("/api/v1/admin/editorial/top-stories?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert data[0]["status"] == "ACTIVE"
        assert "unique_readers" in data[0]

@pytest.mark.asyncio
async def test_admin_editorial_review_queue(db_session: AsyncSession, client: TestClient):
    decision = StoryAssignmentDecision(
        article_id="art-rev-1",
        candidate_story_id="story-1",
        similarity_score=0.85,
        threshold_used=0.80,
        decision="EDITOR_REVIEW"
    )
    db_session.add(decision)
    await db_session.commit()

    response = client.get("/api/v1/admin/editorial/review-queue")
    assert response.status_code == 200
    data = response.json()
    assert "article_drafts" in data
    assert "assignment_reviews" in data
    assert len(data["assignment_reviews"]) >= 1
