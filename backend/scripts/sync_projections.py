import asyncio
import logging
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.tnt.projectors import ArticleProjector
from app.core.database import AsyncSessionLocal
from app.core.projection.engine import ProjectionEngine
from app.models.article import ProcessedArticle
from app.models.event import EventCategory, EventEnvelope, EventSubjectType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if os.environ.get("ALLOW_DESTRUCTIVE_OPERATIONS", "false").lower() != "true":
    raise RuntimeError("Aborted. Must run with ALLOW_DESTRUCTIVE_OPERATIONS=true to prevent accidental data loss.")

class ProjectionRepairService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.engine = ProjectionEngine(session)
        self.article_projector = ArticleProjector()

    async def run_repair(self):
        logger.info("Starting Projection Repair...")

        pa_stmt = select(ProcessedArticle).where(ProcessedArticle.published_status == 'published')
        pa_res = await self.session.execute(pa_stmt)
        processed_articles = pa_res.scalars().all()

        replayed = 0
        for pa in processed_articles:
            artifact_id = f"editorial_{pa.id}"

            article_data = {
                "id": artifact_id,
                "url": f"https://technewstoday.com/articles/{pa.slug}",
                "canonical_url": f"https://technewstoday.com/articles/{pa.slug}",
                "title": pa.title,
                "subtitle": "",
                "author": "TNT Editorial",
                "published_at": pa.published_at.isoformat() if pa.published_at else None,
                "updated_at": pa.updated_at.isoformat() if hasattr(pa, 'updated_at') and pa.updated_at else None,
                "language": "en",
                "summary": pa.summary,
                "content": pa.content,
                "word_count": len(pa.content.split()) if pa.content else 0,
                "reading_time": pa.reading_time,
                "images": [],
                "tags": pa.tags.split(',') if pa.tags else [],
                "source": pa.source_name,
                "license": "Copyright",
                "hash": pa.thumbnail_hash or "hash",
                "thumbnail_url": pa.thumbnail_url,
                "thumbnail_local": pa.thumbnail_local,
                "is_test_data": pa.is_test_data
            }

            # Trigger ArticleProjector manually (because it's not in projector_registry)
            await self.article_projector.project(artifact_id, article_data, self.session)

            # Create synthetic EventEnvelope for ProjectionEngine (so other pure projectors trigger)
            synthetic_event = EventEnvelope(
                category=EventCategory.EDITORIAL,
                event_type="ArticlePublished",
                subject_type=EventSubjectType.ARTICLE,
                subject_id=artifact_id,
                provider="INTERNAL",
                payload=article_data,
                occurred_at=pa.published_at,
                received_at=pa.published_at
            )

            # Process via ProjectionEngine
            await self.engine.process_event(synthetic_event, dry_run=False)

            replayed += 1

        logger.info(f"Replayed {replayed} projections.")
        logger.info("Projection Repair Service Finished.")


async def main():
    async with AsyncSessionLocal() as session:
        service = ProjectionRepairService(session)
        await service.run_repair()

if __name__ == "__main__":
    asyncio.run(main())
