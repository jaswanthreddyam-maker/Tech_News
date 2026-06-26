from typing import Any

from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import IncrementMutation, ProjectionBatch, UpsertMutation
from app.core.projection.policy import ConsistencyMode, ProjectionPolicy
from app.core.projection.projector import Projector
from app.models.recommendation import ArticleFeatureVector


class PopularityProjector(Projector):
    """
    Computes deterministic popularity scores based on views and completions.
    """
    @property
    def projection_group(self) -> str:
        return "recommendations"

    @property
    def name(self) -> str:
        return "PopularityProjector"

    @property
    def version(self) -> int:
        return 1

    @property
    def supported_events(self) -> list[str]:
        return ["ARTICLE_VIEWED", "ARTICLE_COMPLETED"]

    @property
    def policy(self) -> ProjectionPolicy:
        return ProjectionPolicy(
            consistency=ConsistencyMode.EXACTLY_ONCE,
            priority="HIGH",
            batch_size=200,
            parallelism=2
        )

    async def project(self, event: Any, context: ProjectionContext) -> ProjectionBatch:
        batch = ProjectionBatch(version=self.version)

        article_id = event.subject_id

        # We assume the article feature vector exists or we upsert it
        # Popularity score logic:
        # view = +1.0
        # completion = +3.0

        score_increment = 0.0
        if event.event_type == "ARTICLE_VIEWED":
            score_increment = 1.0
        elif event.event_type == "ARTICLE_COMPLETED":
            score_increment = 3.0

        if score_increment > 0:
            # We can use UpsertMutation to safely create or update
            # Since Upsert currently replaces exactly, we might want an IncrementMutation
            # Wait, our IncrementMutation takes a `where` clause.
            batch.add(
                IncrementMutation(
                    model=ArticleFeatureVector,
                    target_id=article_id,
                    field="engagement_score",
                    amount=score_increment
                )
            )
            # Ensure the row exists by first yielding an Upsert with default values
            # if it doesn't exist. But to avoid overriding, we can check existence.
            exists = await context.exists(ArticleFeatureVector, {"article_id": article_id})
            if not exists:
                batch.add(
                    UpsertMutation(
                        model=ArticleFeatureVector,
                        target_id=article_id,
                        values={"article_id": article_id}
                    )
                )

        return batch

from app.core.projection.registry import projector_registry

projector_registry.register(PopularityProjector())
