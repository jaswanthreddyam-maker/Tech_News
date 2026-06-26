import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import WorkspaceActivity, WorkspaceEventType

logger = logging.getLogger("tech_news.services.activity_logger")


class ActivityLogger:
    """
    Decoupled logger for workspace domain events.
    Eventually, this can publish to a message broker (e.g. Kafka/RabbitMQ)
    or be part of a broader Domain Events layer.
    """

    @staticmethod
    async def log(
        db: AsyncSession,
        workspace_id: int,
        event_type: WorkspaceEventType,
        actor_type: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
    ) -> WorkspaceActivity:
        """
        Logs a workspace activity event.
        """
        try:
            activity = WorkspaceActivity(
                workspace_id=workspace_id,
                event_type=event_type.value,
                actor_type=actor_type,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata_payload=metadata or {},
            )
            db.add(activity)
            # We don't commit here, we let the caller commit the transaction
            # so the event is atomic with the action it represents.
            return activity
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            raise
