import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.article import ProcessedArticle
from app.core.events.models import EventOutbox
from app.apps.tnt.projectors import ArticleProjector
from app.core.metrics.replay import replay_metrics
from app.core.event_bus import publish_event
import logging

logger = logging.getLogger(__name__)

class ReplayService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.projector = ArticleProjector()

    async def _emit_audit(self, event_name: str, payload: dict):
        """Internal helper to emit the Replay Audit Trail to the global SSE event bus."""
        await publish_event("REPLAY_SYSTEM", event_name, status="info", metadata=payload)

    async def replay_projection(self, article_id: str, admin_email: str) -> bool:
        start_time = time.time()
        replay_metrics.requests_total.labels(type="projection").inc()
        await self._emit_audit("ProjectionReplayRequested", {"article_id": article_id, "admin": admin_email})

        try:
            stmt = select(ProcessedArticle).where(ProcessedArticle.id == article_id)
            res = await self.session.execute(stmt)
            article = res.scalars().first()
            if not article:
                raise ValueError(f"ProcessedArticle {article_id} not found.")

            # Synthesize payload for projector
            article_data = {
                "url": article.url,
                "canonical_url": getattr(article, "canonical_url", None),
                "title": article.title,
                "subtitle": getattr(article, "subtitle", None),
                "author": getattr(article, "author", None),
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "updated_at": getattr(article, "updated_at", None),
                "language": getattr(article, "language", "en"),
                "summary": article.summary,
                "content": article.content,
                "word_count": getattr(article, "word_count", 0),
                "reading_time": getattr(article, "reading_time", 0),
                "images": getattr(article, "images", []),
                "tags": article.tags,
                "source": article.source_name,
                "license": getattr(article, "license", None),
                "hash": article.hash,
                "thumbnail_url": article.thumbnail_url,
                "thumbnail_local": getattr(article, "thumbnail_local", None),
                "key_takeaways": getattr(article, "key_takeaways", None),
                "is_test_data": getattr(article, "is_test_data", False),
                "impact_score": getattr(article, "final_score", 0.0),
                "freshness_score": getattr(article, "freshness_score", 0.0),
                "engagement_score": getattr(article, "engagement_score", 0.0),
                "final_score": getattr(article, "final_score", 0.0),
                "category": getattr(article, "category", None),
                "published_status": article.published_status
            }

            # Execute idempotent projection
            await self.projector.project(str(article.id), article_data, self.session)

            replay_metrics.success_total.labels(type="projection").inc()
            duration = time.time() - start_time
            replay_metrics.duration_seconds.labels(type="projection").observe(duration)
            await self._emit_audit("ProjectionReplayCompleted", {"article_id": article_id, "admin": admin_email, "duration": duration})
            return True

        except Exception as e:
            replay_metrics.failure_total.labels(type="projection").inc()
            await self._emit_audit("ProjectionReplayFailed", {"article_id": article_id, "admin": admin_email, "error": str(e)})
            raise e

    async def replay_event(self, event_id: int, admin_email: str) -> bool:
        start_time = time.time()
        replay_metrics.requests_total.labels(type="event").inc()
        await self._emit_audit("EventReplayRequested", {"event_id": event_id, "admin": admin_email})

        try:
            # Rescheduling the event is completely idempotent and lets the BackgroundDispatcher handle it
            stmt = (
                update(EventOutbox)
                .where(EventOutbox.id == event_id)
                .values(status="CREATED", retry_count=0, lease_id=None, lease_expires_at=None)
            )
            res = await self.session.execute(stmt)
            if res.rowcount == 0:
                raise ValueError(f"EventOutbox {event_id} not found.")
            
            await self.session.commit()

            replay_metrics.success_total.labels(type="event").inc()
            duration = time.time() - start_time
            replay_metrics.duration_seconds.labels(type="event").observe(duration)
            await self._emit_audit("EventReplayCompleted", {"event_id": event_id, "admin": admin_email, "duration": duration})
            return True

        except Exception as e:
            await self.session.rollback()
            replay_metrics.failure_total.labels(type="event").inc()
            await self._emit_audit("EventReplayFailed", {"event_id": event_id, "admin": admin_email, "error": str(e)})
            raise e

    async def replay_failed_batch(self, admin_email: str) -> int:
        start_time = time.time()
        replay_metrics.requests_total.labels(type="batch").inc()
        await self._emit_audit("BatchReplayRequested", {"admin": admin_email})

        try:
            # Fetch and reset all FAILED or DEAD_LETTER events
            stmt = (
                update(EventOutbox)
                .where(EventOutbox.status.in_(["FAILED", "DEAD_LETTER"]))
                .values(status="CREATED", retry_count=0, lease_id=None, lease_expires_at=None)
            )
            res = await self.session.execute(stmt)
            updated_count = res.rowcount
            await self.session.commit()

            replay_metrics.success_total.labels(type="batch").inc()
            duration = time.time() - start_time
            replay_metrics.duration_seconds.labels(type="batch").observe(duration)
            await self._emit_audit("BatchReplayCompleted", {"admin": admin_email, "replayed_count": updated_count, "duration": duration})
            return updated_count

        except Exception as e:
            await self.session.rollback()
            replay_metrics.failure_total.labels(type="batch").inc()
            await self._emit_audit("BatchReplayFailed", {"admin": admin_email, "error": str(e)})
            raise e
