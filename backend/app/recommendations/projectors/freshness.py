from typing import Any

from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import ProjectionBatch, SetMutation, UpsertMutation
from app.core.projection.policy import ConsistencyMode, ProjectionPolicy
from app.core.projection.projector import Projector
from app.models.recommendation import ArticleFeatureVector


class FreshnessProjector(Projector):
    """
    Sets the initial freshness score when an article is published.
    """
    @property
    def projection_group(self) -> str:
        return "recommendations"

    @property
    def name(self) -> str:
        return "FreshnessProjector"

    @property
    def version(self) -> int:
        return 1

    @property
    def supported_events(self) -> list[str]:
        return ["ARTICLE_PUBLISHED"]

    @property
    def policy(self) -> ProjectionPolicy:
        return ProjectionPolicy(
            consistency=ConsistencyMode.EXACTLY_ONCE,
            priority="NORMAL",
            batch_size=100
        )

    async def project(self, event: Any, context: ProjectionContext) -> ProjectionBatch:
        batch = ProjectionBatch(version=self.version)

        article_id = event.subject_id

        # When published, freshness is 1.0
        exists = await context.exists(ArticleFeatureVector, {"article_id": article_id})

        if not exists:
            batch.add(
                UpsertMutation(
                    model=ArticleFeatureVector,
                    target_id=article_id,
                    values={"article_id": article_id, "freshness_score": 1.0}
                )
            )
        else:
            batch.add(
                SetMutation(
                    model=ArticleFeatureVector,
                    target_id=article_id,
                    field="freshness_score",
                    value=1.0
                )
            )

        return batch

from app.core.projection.registry import projector_registry

projector_registry.register(FreshnessProjector())
