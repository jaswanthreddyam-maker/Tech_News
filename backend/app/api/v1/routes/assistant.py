import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.assistant.assistant_service import PersonalAssistantService
from app.ai.chat.schemas import OwnerType
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.conversation import ConversationSession
from app.models.memory import ConversationEpisode
from app.models.user import User

logger = logging.getLogger("tech_news.api.v1.assistant")
router = APIRouter(tags=["Assistant"])


class AssistantQueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None


def _verify_session_owner(session: ConversationSession, user_id: int) -> bool:
    if session.user_id is not None and session.user_id == user_id:
        return True
    meta = session.metadata_json or {}
    if meta.get("owner_id") == str(user_id):
        return True
    return False


@router.post("/query")
async def query_assistant(
    body: AssistantQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    owner_type = OwnerType.USER
    owner_id = str(current_user.id)
    conv_id = body.conversation_id

    if conv_id:
        # Validate existing conversation session
        stmt = select(ConversationSession).where(ConversationSession.conversation_id == conv_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session or not _verify_session_owner(session, current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        # Auto-create new conversation session in short-lived transaction
        conv_id = f"ast_conv_{uuid.uuid4().hex[:12]}"
        session = ConversationSession(
            conversation_id=conv_id,
            user_id=current_user.id,
            status="ACTIVE",
            metadata_json={
                "owner_type": owner_type.value,
                "owner_id": owner_id,
                "title": body.query[:40] if body.query else "New Research",
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(session)
        await db.commit()

    # Create User Episode in short-lived transaction
    message_id = f"ast_msg_{uuid.uuid4().hex[:12]}"
    user_episode = ConversationEpisode(
        conversation_id=conv_id,
        user_id=current_user.id,
        role="user",
        message=body.query,
        metadata_json={
            "message_id": message_id,
            "owner_type": owner_type.value,
            "owner_id": owner_id,
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(user_episode)
    await db.commit()

    service = PersonalAssistantService(db)
    generator = service.stream_query(
        query=body.query,
        owner_type=owner_type.value,
        owner_id=owner_id,
        conversation_id=conv_id,
        message_id=message_id,
    )
    async def guarded_stream():
        """Wrap the generator with a hard 90s timeout guard."""
        import asyncio
        try:
            async with asyncio.timeout(90):
                async for chunk in generator:
                    yield chunk
        except TimeoutError:
            yield 'event: error\ndata: {"message": "Request timed out. Please try again."}\n\n'
        except Exception as e:
            logger.error(f"Stream generation error: {e}")
            yield 'event: error\ndata: {"message": "Stream error. Please try again."}\n\n'

    return StreamingResponse(guarded_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@router.get("/conversations")
async def list_assistant_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ConversationSession).where(
        (ConversationSession.user_id == current_user.id)
    ).order_by(ConversationSession.updated_at.desc())
    res = await db.execute(stmt)
    user_sessions = res.scalars().all()

    return {
        "conversations": [
            {
                "conversation_id": s.conversation_id,
                "title": (s.metadata_json or {}).get("title", "New Research"),
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in user_sessions
        ]
    }


@router.get("/conversations/{conversation_id}")
async def get_assistant_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ConversationSession).where(ConversationSession.conversation_id == conversation_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if not session or not _verify_session_owner(session, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    ep_stmt = (
        select(ConversationEpisode)
        .where(ConversationEpisode.conversation_id == conversation_id)
        .order_by(ConversationEpisode.created_at.asc())
    )
    ep_res = await db.execute(ep_stmt)
    episodes = ep_res.scalars().all()

    return {
        "conversation_id": session.conversation_id,
        "title": (session.metadata_json or {}).get("title", "New Research"),
        "messages": [
            {
                "id": (ep.metadata_json or {}).get("message_id", f"ep_{ep.id}"),
                "role": ep.role,
                "content": ep.message,
                "sources": (ep.metadata_json or {}).get("sources"),
                "created_at": ep.created_at.isoformat() if ep.created_at else None,
            }
            for ep in episodes
        ],
    }

