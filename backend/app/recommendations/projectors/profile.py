from typing import Any

from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import MergeMutation, ProjectionBatch, UpsertMutation
from app.core.projection.policy import ConsistencyMode, ProjectionPolicy
from app.core.projection.projector import Projector
from app.models.recommendation import RecommendationProfile


class RecommendationProfileProjector(Projector):
    @property
    def projection_group(self) -> str:
        return "recommendations"

    @property
    def name(self) -> str:
        return "RecommendationProfileProjector"

    @property
    def version(self) -> int:
        return 1

    @property
    def supported_events(self) -> list[str]:
        return ["ARTICLE_PUBLISHED", "ARTICLE_VIEWED", "ARTICLE_COMPLETED"]

    @property
    def policy(self) -> ProjectionPolicy:
        return ProjectionPolicy(
            consistency=ConsistencyMode.EXACTLY_ONCE,
            parallelism=2
        )

    async def project(self, event: Any, context: ProjectionContext) -> ProjectionBatch:
        batch = ProjectionBatch(version=self.version)

        article_id = event.subject_id
        if not article_id:
            return batch

        exists = await context.exists(RecommendationProfile, {"article_id": article_id})
        if not exists:
            batch.add(
                UpsertMutation(
                    model=RecommendationProfile,
                    target_id=article_id,
                    values={"article_id": article_id, "ranking_features": {}, "context_features": {}}
                )
            )

        if event.event_type == "ARTICLE_PUBLISHED":
            batch.add(
                MergeMutation(
                    model=RecommendationProfile,
                    target_id=article_id,
                    field="ranking_features",
                    data={"freshness": 1.0, "editorial": 1.0}
                )
            )
        elif event.event_type in ["ARTICLE_VIEWED", "ARTICLE_COMPLETED"]:
            # Example logic for simple tracking. In a real system we might read existing profile to increment 
            # or just emit an engagement increment. However, MergeMutation only replaces jsonb keys, doesn't increment them.
            # To increment inside JSONB without complex SQL, we read current state.
            profile = await context.load(RecommendationProfile, {"article_id": article_id})
            if profile:
                ranking = profile.ranking_features or {}
                current_engagement = ranking.get("engagement", 0.0)

                score_increment = 1.0 if event.event_type == "ARTICLE_VIEWED" else 3.0
                batch.add(
                    MergeMutation(
                        model=RecommendationProfile,
                        target_id=article_id,
                        field="ranking_features",
                        data={"engagement": current_engagement + score_increment}
                    )
                )

        return batch

from app.core.projection.registry import projector_registry

projector_registry.register(RecommendationProfileProjector())
