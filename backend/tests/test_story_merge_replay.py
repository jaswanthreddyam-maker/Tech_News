import pytest
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.story import Story, StoryStatus, StoryTimelineEvent
from app.models.article import ProcessedArticle
from app.core.events.models import EventOutbox
from app.apps.tnt.projectors import ArticleProjector, StoryProjector
from sqlalchemy import select

@pytest.mark.asyncio
async def test_story_merge_replay_idempotency(db_session: AsyncSession):
    # Setup Target Story 1 and Source Story 2
    story_1_id = str(uuid.uuid4())
    story_2_id = str(uuid.uuid4())

    story_1 = Story(id=story_1_id, title="Target", status=StoryStatus.ACTIVE)
    story_2 = Story(id=story_2_id, title="Source", status=StoryStatus.ACTIVE)
    db_session.add_all([story_1, story_2])

    # Add Articles A, B, C to Story 2
    from app.models.article import ArticleReadModel
    articles = []
    for letter in ["A", "B", "C"]:
        article = ArticleReadModel(
            id=f"test-article-{letter}",
            title=f"Article {letter}",
            url=f"http://test.com/{letter}",
            content=f"Content {letter}",
            source="test-source",
            hash=f"hash-{letter}",
            story_id=story_2_id,
            language="en",
            word_count=0,
            reading_time=0,
            images=[],
            tags=[],
            thumbnail_type="REAL_IMAGE",
            editorial_status="DRAFT"
        )
        articles.append(article)
        db_session.add(article)

    await db_session.flush()

    # Create Outbox Event
    payload = {
        "story_id": story_1_id,
        "source_story_id": story_2_id,
        "merged_article_count": 3,
        "merged_by": "editor",
        "reason": "Test merge"
    }
    event = EventOutbox(event_type="StoriesMerged", payload=payload)
    db_session.add(event)
    await db_session.flush()
    event_id = event.id

    # Initialize Projectors
    article_projector = ArticleProjector()
    story_projector = StoryProjector()

    async def run_merge():
        await article_projector.handle_stories_merged(payload, db_session)
        await story_projector.handle_timeline_event("StoriesMerged", payload, event_id, db_session)
        # Simulate the API handler archiving the source story
        source_st = await db_session.get(Story, story_2_id)
        source_st.status = StoryStatus.ARCHIVED

    # First Merge
    await run_merge()
    
    # Verify First Merge
    from sqlalchemy import select
    res_articles = await db_session.execute(select(ArticleReadModel).where(ArticleReadModel.id.in_(["test-article-A", "test-article-B", "test-article-C"])))
    for a in res_articles.scalars():
        assert a.story_id == story_1_id
        
    res_timeline = await db_session.execute(select(StoryTimelineEvent).where(StoryTimelineEvent.source_event_id == event_id))
    assert len(res_timeline.all()) == 1

    # Story 2 -> ARCHIVED
    st_2_after = await db_session.get(Story, story_2_id)
    assert st_2_after.status == StoryStatus.ARCHIVED

    # Replay Same Event
    await run_merge()

    # Verify No Duplicates
    res_timeline_2 = await db_session.execute(select(StoryTimelineEvent).where(StoryTimelineEvent.source_event_id == event_id))
    assert len(res_timeline_2.all()) == 1

    # Replay Again
    await run_merge()
    res_timeline_3 = await db_session.execute(select(StoryTimelineEvent).where(StoryTimelineEvent.source_event_id == event_id))
    assert len(res_timeline_3.all()) == 1
