import uuid

from fastapi import Depends, Request

from app.ai.chat.schemas import OwnerType
from app.core.security import get_current_user_optional
from app.models.user import User


async def resolve_owner(
    request: Request, user: User | None = Depends(get_current_user_optional)
) -> tuple[OwnerType, str]:
    """
    Canonical ownership resolver.
    Determines owner from validated JWT (Current User) or anonymous client_id cookie.
    """
    if user and getattr(user, "id", None):
        return OwnerType.USER, str(user.id)

    # Fall back to anonymous client_id cookie
    client_id = request.cookies.get("client_id")
    if not client_id:
        # In a real scenario we might want to reject this, but for now we follow the existing pattern
        client_id = str(uuid.uuid4())
    return OwnerType.ANONYMOUS, client_id
