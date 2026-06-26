import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.models import EventOutbox
from app.models.article import ProcessedArticle

logger = logging.getLogger(__name__)

class ThumbnailUpdatedApplicationService:
    @staticmethod
    async def finalize_thumbnail_update(
        db: AsyncSession,
        article_id: int,
        thumbnail_url: str,
        thumbnail_local: str,
        thumbnail_hash: str,
        thumbnail_source: str,
        candidate_count: int,
        winner_pass: str,
        thumbnail_score: int,
        thumbnail_type: str = "REAL_IMAGE",
        thumbnail_generation_reason: str | None = None,
    ) -> ProcessedArticle | None:
        """
        Updates the ProcessedArticle with the new thumbnail information and
        emits an ArticleThumbnailUpdated domain event for the CQRS read model projection.
        """
        stmt = select(ProcessedArticle).where(ProcessedArticle.id == article_id)
        res = await db.execute(stmt)
        art = res.scalars().first()

        if not art:
            logger.warning(f"ThumbnailService: ProcessedArticle {article_id} not found.")
            return None

        # 1. Update source of truth
        art.thumbnail_url = thumbnail_url
        art.thumbnail_local = thumbnail_local
        art.thumbnail_status = "downloaded" if thumbnail_source != "fallback" else "failed"
        if thumbnail_type == "AI_GENERATED":
            art.thumbnail_status = "downloaded"  # Treat AI generation as successful download
        art.thumbnail_hash = thumbnail_hash
        art.thumbnail_source = thumbnail_source
        art.image_url = thumbnail_local
        art.hero_image = thumbnail_local
        art.candidate_count = candidate_count
        art.winner_pass = winner_pass
        art.thumbnail_score = thumbnail_score
        art.thumbnail_algorithm_version = "v1"
        art.thumbnail_type = thumbnail_type
        art.thumbnail_generation_reason = thumbnail_generation_reason
        if thumbnail_type == "AI_GENERATED":
            art.thumbnail_generated_at = datetime.now(timezone.utc)

        # 2. Emit Domain Event (ArticleThumbnailUpdated) via Outbox
        occurred_at = datetime.now(timezone.utc)
        payload = {
            "article_id": str(art.id),
            "thumbnail_local": art.thumbnail_local,
            "thumbnail_url": art.thumbnail_url,
            "thumbnail_hash": art.thumbnail_hash,
            "status": art.thumbnail_status,
            "thumbnail_type": art.thumbnail_type,
            "occurred_at": occurred_at.isoformat(),
        }

        outbox_event = EventOutbox(
            event_type="ArticleThumbnailUpdated",
            payload=payload,
        )
        db.add(outbox_event)

        # Trigger scoring coordinator for thumbnail stage
        from app.editorial.coordinator import ArticleEnrichmentCoordinator
        await ArticleEnrichmentCoordinator.mark_stage_complete(db, art.id, "thumbnail")

        # 3. Commit transaction
        await db.commit()

        logger.info(f"ThumbnailService: Updated thumbnail for article {article_id} and emitted ArticleThumbnailUpdated event.")
        return art

