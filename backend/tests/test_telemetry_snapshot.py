import pytest
from datetime import datetime, timezone

from app.models.story import Story, StoryStatus
from app.models.article import ArticleReadModel
from app.models.analytics import ArticleMetrics, StoryTelemetrySnapshot
from app.tasks.telemetry_tasks import capture_snapshots_async
from app.models.user import SavedArticle

@pytest.mark.asyncio
async def test_capture_story_telemetry_snapshots(db_session):
    # Setup test data
    now = datetime.now(timezone.utc)
    
    # Create Story
    story = Story(
        id="test-telemetry-story",
        title="Test Telemetry Story",
        status=StoryStatus.ACTIVE,
        created_at=now
    )
    db_session.add(story)
    
    # Create Articles
    article1 = ArticleReadModel(
        id="test-telemetry-art-1",
        title="Article 1",
        url="http://test.com/art1",
        content="content 1",
        source="test-source",
        hash="hash1",
        story_id=story.id,
        language="en",
        word_count=0,
        reading_time=0,
        images=[],
        tags=[],
        thumbnail_type="REAL_IMAGE",
        editorial_status="DRAFT"
    )
    article2 = ArticleReadModel(
        id="test-telemetry-art-2",
        title="Article 2",
        url="http://test.com/art2",
        content="content 2",
        source="test-source",
        hash="hash2",
        story_id=story.id,
        language="en",
        word_count=0,
        reading_time=0,
        images=[],
        tags=[],
        thumbnail_type="REAL_IMAGE",
        editorial_status="DRAFT"
    )
    db_session.add_all([article1, article2])
    
    # Create Metrics
    am1 = ArticleMetrics(
        article_id=article1.id,
        views=100,
        unique_views=80,
        avg_read_time_seconds=60.0
    )
    am2 = ArticleMetrics(
        article_id=article2.id,
        views=50,
        unique_views=40,
        avg_read_time_seconds=30.0
    )
    db_session.add_all([am1, am2])
    
    from app.models.user import User
    test_user = User(
        id=999,
        name="Test User",
        email="test@user.com"
    )
    db_session.add(test_user)

    # Create SavedArticle (bookmark)
    sa = SavedArticle(
        id=9999,
        user_id=test_user.id,
        article_id=article1.id,
        created_at=now
    )
    
    # Create Reawaken event
    from app.models.story import StoryTimelineEvent
    reawaken_event = StoryTimelineEvent(
        story_id=story.id,
        event_type='StoryReawakened',
        occurred_at=now,
        payload={}
    )
    db_session.add_all([sa, reawaken_event])
    
    await db_session.commit()
    
    # Run Task
    await capture_snapshots_async(db_session)
    
    # Verify Snapshot
    from sqlalchemy import select
    stmt = select(StoryTelemetrySnapshot).where(StoryTelemetrySnapshot.story_id == story.id)
    result = await db_session.execute(stmt)
    snapshot = result.scalar_one_or_none()
    
    assert snapshot is not None
    assert snapshot.story_status == "ACTIVE"
    assert snapshot.views == 150
    assert snapshot.unique_readers == 120
    assert snapshot.avg_read_time_seconds == 45.0  # (60 + 30) / 2
    assert snapshot.avg_completion_rate == 0.0  # default
    assert snapshot.reawaken_count == 1
    assert snapshot.bookmarks == 1
    assert snapshot.newsletter_deliveries == 0
    assert snapshot.newsletter_clicks == 0
    assert snapshot.article_count == 2
    assert snapshot.snapshot_version == 1
    assert snapshot.story_age_hours >= 0.0
