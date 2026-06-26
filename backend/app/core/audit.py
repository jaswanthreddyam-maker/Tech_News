import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import correlation_id_ctx
from app.models.user import AuditLog

logger = logging.getLogger("tech_news.audit")


async def log_audit(
    db: AsyncSession,
    action: str,
    resource: str,
    user_id: int | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    device: str | None = None,
) -> AuditLog:
    """
    Create an audit log entry for administrative actions.

    Args:
        db: Active async database session.
        user_id: ID of the user performing the action.
        action: Description of the action performed.
        resource: The resource type/identifier affected.
        metadata: Optional JSONB metadata dict with action details.
        ip_address: Client IP address from the request.
        device: User-Agent or device identifier string.

    Returns:
        The created AuditLog record.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        metadata_=metadata or {},
        ip_address=ip_address,
        device=device,
    )

    db.add(audit_entry)
    await db.flush()

    logger.info(
        f"Audit log created: user={user_id} action={action} resource={resource}",
        extra={
            "extra_data": {
                "correlation_id": correlation_id,
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "metadata": metadata,
            }
        },
    )

    return audit_entry
