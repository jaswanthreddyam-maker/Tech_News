from typing import Any

from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import IncrementMutation, InsertMutation, ProjectionBatch
from app.core.projection.policy import ConsistencyMode, ProjectionPolicy
from app.core.projection.projector import Projector
from app.models.recommendation import AffinitySubjectType, UserAffinityProfile


class UserAffinityProjector(Projector):
    """
    Updates user affinity profiles based on implicit and explicit actions.
    """
    @property
    def projection_group(self) -> str:
        return "recommendations"

    @property
    def name(self) -> str:
        return "UserAffinityProjector"

    @property
    def version(self) -> int:
        return 1

    @property
    def supported_events(self) -> list[str]:
        return ["TOPIC_FOLLOWED", "ENTITY_FOLLOWED"]

    @property
    def policy(self) -> ProjectionPolicy:
        return ProjectionPolicy(
            consistency=ConsistencyMode.EXACTLY_ONCE,
            priority="HIGH",
            batch_size=50
        )

    async def project(self, event: Any, context: ProjectionContext) -> ProjectionBatch:
        batch = ProjectionBatch(version=self.version)

        user_id = event.provider if event.provider else "anonymous"
        # Wait, usually subject_type is user, but here subject_id is the topic id

        subject_type = None
        subject_id = event.subject_id

        if event.event_type == "TOPIC_FOLLOWED":
            subject_type = AffinitySubjectType.TOPIC
        elif event.event_type == "ENTITY_FOLLOWED":
            subject_type = AffinitySubjectType.ENTITY

        if subject_type:
            # Check if exists
            exists = await context.exists(UserAffinityProfile, {
                "user_id": user_id, 
                "subject_type": subject_type, 
                "subject_id": subject_id
            })

            if not exists:
                batch.add(
                    InsertMutation(
                        model=UserAffinityProfile,
                        values={
                            "user_id": user_id,
                            "subject_type": subject_type,
                            "subject_id": subject_id,
                            "weight": 1.0,
                            "source": "explicit"
                        }
                    )
                )
            else:
                # We need to increment the weight. But IncrementMutation requires target_id which maps to a single column.
                # Since UserAffinityProfile pk is `id`, we must load the id first to use IncrementMutation!
                profile = await context.load(UserAffinityProfile, {
                    "user_id": user_id, 
                    "subject_type": subject_type, 
                    "subject_id": subject_id
                })
                if profile:
                    batch.add(
                        IncrementMutation(
                            model=UserAffinityProfile,
                            target_id=profile.id,
                            field="weight",
                            amount=1.0
                        )
                    )

        return batch

from app.core.projection.registry import projector_registry

projector_registry.register(UserAffinityProjector())
