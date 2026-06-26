
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import Permission
from app.core.security import require_permission
from app.services.recipient_service import AudienceService, SubscriberService

router = APIRouter()

@router.post("/subscribers")
async def create_subscriber(
    email: str,
    display_name: str | None = None,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FULL_ADMIN))
):
    service = SubscriberService(db)
    sub = await service.get_or_create_subscriber(primary_email=email, display_name=display_name, user_id=user_id)
    return {"id": sub.id, "email": sub.primary_email, "status": sub.status}

@router.post("/audiences")
async def create_audience(
    name: str,
    description: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FULL_ADMIN))
):
    service = AudienceService(db)
    aud = await service.create_audience(name=name, description=description)
    return {"id": aud.id, "name": aud.name}

@router.post("/subscribers/{subscriber_id}/subscribe")
async def subscribe_to_audience(
    subscriber_id: int,
    audience_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.FULL_ADMIN))
):
    service = SubscriberService(db)
    sub = await service.subscribe_to_audience(subscriber_id, audience_id)
    return {"id": sub.id, "status": sub.status, "audience_id": sub.audience_id}
