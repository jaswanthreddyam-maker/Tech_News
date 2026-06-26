import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat.conversation_registry import ConversationRegistry
from app.ai.chat.conversation_service import ConversationService
from app.ai.chat.memory import MemoryManager
from app.ai.chat.schemas import ComparisonContext, ConversationMetadata, ConversationMode, OwnerType
from app.api.deps import resolve_owner
from app.core.database import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class CreateConversationRequest(BaseModel):
    mode: ConversationMode = ConversationMode.GENERAL
    article_id: int | None = None
    workspace_id: int | None = None


class CreateConversationResponse(BaseModel):
    conversation_id: str
    metadata: ConversationMetadata


class ChatStreamRequest(BaseModel):
    conversation_id: str
    message: str
    mode: ConversationMode = ConversationMode.GENERAL
    article_id: int | None = None
    workspace_id: int | None = None
    context_a: ComparisonContext | None = None
    context_b: ComparisonContext | None = None


class RenameRequest(BaseModel):
    title: str


class ConversationListResponse(BaseModel):
    conversations: list[ConversationMetadata]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    body: CreateConversationRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
):
    """Explicitly creates a new conversation and returns its ID."""
    owner_type, owner_id = owner_info
    registry = ConversationRegistry()
    conversation_id = str(uuid.uuid4())

    meta = await registry.create(
        conversation_id=conversation_id,
        owner_type=owner_type,
        owner_id=owner_id,
        mode=body.mode,
        article_id=body.article_id,
        workspace_id=body.workspace_id,
    )

    response = CreateConversationResponse(conversation_id=conversation_id, metadata=meta)

    # If anonymous, set a client_id cookie so the user can retrieve history
    http_response = response  # FastAPI will serialize this
    # Note: cookie setting is handled in middleware or manually below if needed.
    return response


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(owner_info: tuple[OwnerType, str] = Depends(resolve_owner)):
    """Lists conversations for the current user (authenticated or anonymous)."""
    owner_type, owner_id = owner_info
    registry = ConversationRegistry()

    conversations = await registry.list_conversations(owner_type=owner_type, owner_id=owner_id, limit=50)
    return ConversationListResponse(conversations=conversations)


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, owner_info: tuple[OwnerType, str] = Depends(resolve_owner)):
    """Retrieves conversation metadata and full message history."""
    owner_type, owner_id = owner_info
    registry = ConversationRegistry()

    # Ownership validation
    is_owner = await registry.validate_ownership(conversation_id, owner_type, owner_id)
    if not is_owner:
        raise HTTPException(status_code=404, detail="Conversation not found")

    meta = await registry.get(conversation_id)
    memory = MemoryManager()
    messages, summary = await memory.get_context(conversation_id)

    return {
        "metadata": meta.model_dump() if meta else {},
        "messages": [m.model_dump() for m in messages],
        "summary": summary,
    }


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: str,
    body: RenameRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
):
    """Manually renames a conversation."""
    owner_type, owner_id = owner_info
    registry = ConversationRegistry()

    is_owner = await registry.validate_ownership(conversation_id, owner_type, owner_id)
    if not is_owner:
        raise HTTPException(status_code=404, detail="Conversation not found")

    success = await registry.rename(conversation_id, body.title)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "renamed", "title": body.title}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, owner_info: tuple[OwnerType, str] = Depends(resolve_owner)):
    """Deletes a conversation and all associated Redis data."""
    owner_type, owner_id = owner_info
    registry = ConversationRegistry()

    is_owner = await registry.validate_ownership(conversation_id, owner_type, owner_id)
    if not is_owner:
        raise HTTPException(status_code=404, detail="Conversation not found")

    success = await registry.delete(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "deleted"}


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    """
    Streams the conversational AI response using Server-Sent Events (SSE).
    Requires an existing conversation_id from POST /conversations.
    """
    owner_type, owner_id = owner_info
    registry = ConversationRegistry()

    # Validate ownership
    is_owner = await registry.validate_ownership(body.conversation_id, owner_type, owner_id)
    if not is_owner:
        raise HTTPException(status_code=404, detail="Conversation not found")

    service = ConversationService(db)

    return StreamingResponse(
        service.stream_chat(
            conversation_id=body.conversation_id,
            message=body.message,
            mode=body.mode,
            article_id=body.article_id,
            workspace_id=body.workspace_id,
            context_a=body.context_a,
            context_b=body.context_b,
        ),
        media_type="text/event-stream",
    )
