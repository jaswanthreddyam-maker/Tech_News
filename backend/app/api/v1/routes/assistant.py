import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.assistant.assistant_service import PersonalAssistantService
from app.ai.chat.schemas import OwnerType
from app.api.deps import resolve_owner
from app.core.database import get_db

logger = logging.getLogger("tech_news.api.v1.assistant")
router = APIRouter(tags=["Assistant"])


class AssistantQueryRequest(BaseModel):
    query: str


@router.post("/query")
async def query_assistant(
    body: AssistantQueryRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = PersonalAssistantService(db)

    generator = service.stream_query(query=body.query, owner_type=owner_type.value, owner_id=owner_id)
    return StreamingResponse(generator, media_type="text/event-stream")
