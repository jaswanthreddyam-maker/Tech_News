
from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import IncrementMutation, InsertMutation, ProjectionBatch, SetMutation
from app.core.projection.projector import Projector
from app.models.analytics import ArticleMetrics
from app.models.event import EventEnvelope


class ArticleMetricsProjector(Projector):
    @property
    def projection_group(self) -> str:
        return "analytics"

    @property
    def name(self) -> str:
        return "ArticleMetricsProjector"

    @property
    def version(self) -> int:
        return 2

    @property
    def supported_events(self) -> list[str]:
        return [
            "ARTICLE_VIEWED",
            "ARTICLE_COMPLETED",
            "ARTICLE_SHARED"
        ]

    async def project(self, event: EventEnvelope, context: ProjectionContext) -> ProjectionBatch:
        batch = ProjectionBatch(version=self.version)

        article_id = event.subject_id
        if not article_id:
            return batch

        # Load current state
        metrics = await context.load(ArticleMetrics, article_id)

        if not metrics:
            # Need to create it first
            batch.add(InsertMutation(
                model=ArticleMetrics,
                values={
                    "article_id": article_id,
                    "views": 0, "unique_views": 0, "total_read_time_seconds": 0,
                    "avg_read_time_seconds": 0.0, "completed_reads": 0,
                    "completion_rate": 0.0, "shares": 0,
                    "projection_version": self.version
                }
            ))
            # Mock default values for the rest of the logic
            views = 0
            unique_views = 0
            completed_reads = 0
            total_read_time_seconds = 0
        else:
            views = metrics.views
            unique_views = metrics.unique_views
            completed_reads = metrics.completed_reads
            total_read_time_seconds = metrics.total_read_time_seconds

        payload = event.payload or {}

        if event.event_type == "ARTICLE_VIEWED":
            batch.add(IncrementMutation(model=ArticleMetrics, target_id=article_id, field="views", amount=1))
            if payload.get("is_unique_view", False):
                batch.add(IncrementMutation(model=ArticleMetrics, target_id=article_id, field="unique_views", amount=1))

        elif event.event_type == "ARTICLE_COMPLETED":
            batch.add(IncrementMutation(model=ArticleMetrics, target_id=article_id, field="completed_reads", amount=1))

            # Use current loaded state to calculate new completion rate
            new_completed = completed_reads + 1
            if views > 0:
                new_rate = float(new_completed) / float(views)
                batch.add(SetMutation(model=ArticleMetrics, target_id=article_id, field="completion_rate", value=new_rate))

            read_time = payload.get("read_time_seconds", 0)
            if read_time > 0:
                batch.add(IncrementMutation(model=ArticleMetrics, target_id=article_id, field="total_read_time_seconds", amount=read_time))
                new_total_time = total_read_time_seconds + read_time
                if new_completed > 0:
                    new_avg = float(new_total_time) / float(new_completed)
                    batch.add(SetMutation(model=ArticleMetrics, target_id=article_id, field="avg_read_time_seconds", value=new_avg))

        elif event.event_type == "ARTICLE_SHARED":
            batch.add(IncrementMutation(model=ArticleMetrics, target_id=article_id, field="shares", amount=1))

        # We also need to update projection_version to current
        if metrics and metrics.projection_version != self.version:
            batch.add(SetMutation(model=ArticleMetrics, target_id=article_id, field="projection_version", value=self.version))

        return batch

from app.core.projection.registry import projector_registry

projector_registry.register(ArticleMetricsProjector())
