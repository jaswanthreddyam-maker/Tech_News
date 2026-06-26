import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, ArticleReadModel, EditorialStatus
from app.models.story import Story, StoryStatus
from app.api.v1.routes.lifecycle import approve_article, schedule_article, ScheduleRequest, _emit_event
from app.tasks.distribution_tasks import _async_process_event_outbox_task
from app.core.events.models import EventOutbox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_pipeline():
    logger.info("Starting Full Pipeline Verification...")
    
    async with AsyncSessionLocal() as db:
        # 1. Setup Test Data
        story = Story(title="Pipeline Verification Story", status=StoryStatus.ACTIVE)
        db.add(story)
        await db.flush()
        
        from app.models.article import Category
        import uuid
        
        art_id = str(uuid.uuid4())
        
        # Get or create category
        cat = (await db.execute(select(Category).limit(1))).scalars().first()
        if not cat:
            cat = Category(name="Test Category")
            db.add(cat)
            await db.flush()
        
        # Create ProcessedArticle
        proc_art = ProcessedArticle(
            story_id=story.id,
            category_id=cat.id,
            slug=f"pipeline-test-{art_id}",
            title="Pipeline Verification Article",
            summary="Test summary",
            content="Test content",
            source="Internal",
            editorial_status=EditorialStatus.REVIEW
        )
        db.add(proc_art)
        await db.flush()
        
        # Create Read Model
        read_model = ArticleReadModel(
            id=str(proc_art.id),
            story_id=story.id,
            url=f"https://technewstoday.com/{proc_art.slug}",
            title=proc_art.title,
            content=proc_art.content,
            source=proc_art.source,
            hash="testhash",
            editorial_status="REVIEW"
        )
        db.add(read_model)
        await db.commit()
        
        logger.info(f"Created Test Article ID: {proc_art.id}")
        
        # 2. Trigger Lifecycle Events
        await _emit_event(db, proc_art.id, "ArticleApproved", {
            "story_id": story.id,
            "editorial_status": "APPROVED"
        })
        
        now_scheduled = datetime.now(timezone.utc)
        await _emit_event(db, proc_art.id, "ArticleScheduled", {
            "story_id": story.id,
            "publication_status": "SCHEDULED",
            "scheduled_for": now_scheduled.isoformat(),
            "scheduled_by": "test_script"
        })
        await db.commit()
        
        # Check outbox size
        stmt = select(EventOutbox).where(EventOutbox.status == "CREATED")
        outbox_events = (await db.execute(stmt)).scalars().all()
        logger.info(f"Events in Outbox before processing: {len(outbox_events)}")
        
    # 3. Run Worker Processing
    logger.info("Running Outbox Worker...")
    await _async_process_event_outbox_task()
    
    # 4. Verify Projection
    async with AsyncSessionLocal() as db:
        read_model = await db.get(ArticleReadModel, str(proc_art.id))
        
        assert read_model.editorial_status == "APPROVED", f"Expected APPROVED, got {read_model.editorial_status}"
        assert read_model.publication_status == "SCHEDULED", f"Expected SCHEDULED, got {read_model.publication_status}"
        
        logger.info("✅ SUCCESS: ArticleReadModel successfully updated via CQRS pipeline.")
        
        # Cleanup
        await db.delete(read_model)
        proc = await db.get(ProcessedArticle, proc_art.id)
        await db.delete(proc)
        await db.delete(story)
        await db.commit()

if __name__ == "__main__":
    asyncio.run(verify_pipeline())
