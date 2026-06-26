import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat.schemas import OwnerType
from app.api.deps import resolve_owner
from app.core.database import get_db
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger("tech_news.api.v1.workspaces")
router = APIRouter(tags=["Workspaces"])


# --- Schemas ---
class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceRename(BaseModel):
    name: str


class NoteCreate(BaseModel):
    content: str
    title: str | None = None


class NoteUpdate(BaseModel):
    content: str
    title: str | None = None
    summary: str | None = None


class NoteAiRequest(BaseModel):
    operation: str  # SUMMARIZE, EXPAND, REFINE, REWRITE, OUTLINE, FIND_CITATIONS
    selection: str
    full_content: str


class NoteRestoreRequest(BaseModel):
    version_number: int


class PinArticleRequest(BaseModel):
    article_id: int


class AttachConversationRequest(BaseModel):
    conversation_id: str


# --- Helper ---


# --- Endpoints ---
@router.post("", response_model=dict[str, Any])
async def create_workspace(
    body: WorkspaceCreate,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    ws = await service.create_workspace(owner_type.value, owner_id, body.name, body.description)
    return {"id": ws.id, "name": ws.name, "description": ws.description, "created_at": ws.created_at}


@router.get("", response_model=list[dict[str, Any]])
async def list_workspaces(
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner), db: AsyncSession = Depends(get_db)
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    workspaces = await service.list_workspaces(owner_type.value, owner_id)
    return [{"id": w.id, "name": w.name, "created_at": w.created_at, "updated_at": w.updated_at} for w in workspaces]


@router.get("/{workspace_id}", response_model=dict[str, Any])
async def get_workspace(
    workspace_id: int, owner_info: tuple[OwnerType, str] = Depends(resolve_owner), db: AsyncSession = Depends(get_db)
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    ws = await service.get_workspace(workspace_id, owner_type.value, owner_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return {
        "id": ws.id,
        "name": ws.name,
        "description": ws.description,
        "created_at": ws.created_at,
        "articles": [{"article_id": a.article_id, "title": a.article.title} for a in ws.articles],
        "conversations": [{"conversation_id": c.conversation_id} for c in ws.conversations],
        "notes": [
            {"id": n.id, "content": n.content, "created_at": n.created_at, "updated_at": n.updated_at} for n in ws.notes
        ],
    }


@router.patch("/{workspace_id}")
async def rename_workspace(
    workspace_id: int,
    body: WorkspaceRename,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    ws = await service.rename_workspace(workspace_id, owner_type.value, owner_id, body.name)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "success"}


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: int, owner_info: tuple[OwnerType, str] = Depends(resolve_owner), db: AsyncSession = Depends(get_db)
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    success = await service.delete_workspace(workspace_id, owner_type.value, owner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "success"}


# --- Articles ---
@router.post("/{workspace_id}/articles")
async def pin_article(
    workspace_id: int,
    body: PinArticleRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    wa = await service.pin_article(workspace_id, owner_type.value, owner_id, body.article_id)
    if not wa:
        raise HTTPException(status_code=400, detail="Could not pin article")
    return {"status": "success"}


@router.delete("/{workspace_id}/articles/{article_id}")
async def unpin_article(
    workspace_id: int,
    article_id: int,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    success = await service.unpin_article(workspace_id, owner_type.value, owner_id, article_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not unpin article")
    return {"status": "success"}


# --- Notes ---
@router.post("/{workspace_id}/notes")
async def add_note(
    workspace_id: int,
    body: NoteCreate,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    note = await service.add_note(workspace_id, owner_type.value, owner_id, body.content)
    if not note:
        raise HTTPException(status_code=400, detail="Could not add note")
    if body.title:
        note = await service.update_note(
            workspace_id, owner_type.value, owner_id, note.id, body.content, title=body.title
        )
    return {"id": note.id, "title": note.title, "content": note.content}


@router.put("/{workspace_id}/notes/{note_id}")
async def update_note(
    workspace_id: int,
    note_id: int,
    body: NoteUpdate,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    note = await service.update_note(
        workspace_id=workspace_id,
        owner_type=owner_type.value,
        owner_id=owner_id,
        note_id=note_id,
        content=body.content,
        title=body.title,
        summary=body.summary,
    )
    if not note:
        raise HTTPException(status_code=400, detail="Could not update note")
    return {"id": note.id, "content": note.content}


@router.delete("/{workspace_id}/notes/{note_id}")
async def delete_note(
    workspace_id: int,
    note_id: int,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    success = await service.delete_note(workspace_id, owner_type.value, owner_id, note_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not delete note")
    return {"status": "success"}


@router.get("/{workspace_id}/notes/{note_id}/versions")
async def get_note_versions(
    workspace_id: int,
    note_id: int,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    versions = await service.get_note_versions(workspace_id, owner_type.value, owner_id, note_id)
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "change_type": v.change_type,
            "created_by": v.created_by,
            "created_at": v.created_at,
            "content": v.content,
            "summary": v.summary,
        }
        for v in versions
    ]


@router.post("/{workspace_id}/notes/{note_id}/versions/restore")
async def restore_note_version(
    workspace_id: int,
    note_id: int,
    body: NoteRestoreRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    note = await service.restore_note_version(workspace_id, owner_type.value, owner_id, note_id, body.version_number)
    if not note:
        raise HTTPException(status_code=400, detail="Could not restore note version")
    return {
        "status": "success",
        "note": {"id": note.id, "content": note.content, "version_number": note.version_number},
    }


@router.get("/{workspace_id}/notes/{note_id}/backlinks")
async def get_note_backlinks(
    workspace_id: int,
    note_id: int,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    ws_service = WorkspaceService(db)
    # Implicitly verify access by checking if workspace exists
    ws = await ws_service.get_workspace_by_id(workspace_id, owner_type.value, owner_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return await ws_service.get_backlinks(workspace_id, note_id)


@router.get("/{workspace_id}/notes/{note_id}/similar")
async def get_similar_notes(
    workspace_id: int,
    note_id: int,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    ws_service = WorkspaceService(db)
    ws = await ws_service.get_workspace_by_id(workspace_id, owner_type.value, owner_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return await ws_service.get_similar_notes(workspace_id, note_id)


@router.get("/{workspace_id}/notes/search/query")
async def search_notes(
    workspace_id: int,
    q: str,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    ws_service = WorkspaceService(db)
    ws = await ws_service.get_workspace_by_id(workspace_id, owner_type.value, owner_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return await ws_service.search_notes(workspace_id, q)


@router.post("/{workspace_id}/notes/{note_id}/summarize")
async def summarize_note(
    workspace_id: int,
    note_id: int,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    from app.ai.chat.notebook_service import NotebookService

    owner_type, owner_id = owner_info
    service = NotebookService(db)
    summary = await service.summarize_note(workspace_id, note_id, owner_type.value, owner_id)
    if not summary:
        raise HTTPException(status_code=400, detail="Could not summarize note")
    return {"status": "success", "summary": summary}


from fastapi.responses import StreamingResponse


@router.post("/{workspace_id}/notes/{note_id}/ai")
async def ai_note_operation(
    workspace_id: int,
    note_id: int,
    body: NoteAiRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    from app.ai.chat.notebook_service import NotebookService
    from app.models.workspace import NotebookOperation

    owner_type, owner_id = owner_info
    service = NotebookService(db)

    try:
        operation = NotebookOperation(body.operation.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid operation")

    generator = service.stream_operation(
        workspace_id=workspace_id,
        note_id=note_id,
        operation=operation,
        selection=body.selection,
        full_content=body.full_content,
        owner_type=owner_type.value,
        owner_id=owner_id,
    )
    return StreamingResponse(generator, media_type="text/event-stream")


# --- Conversations ---
@router.post("/{workspace_id}/conversations")
async def attach_conversation(
    workspace_id: int,
    body: AttachConversationRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    wc = await service.attach_conversation(workspace_id, owner_type.value, owner_id, body.conversation_id)
    if not wc:
        raise HTTPException(status_code=400, detail="Could not attach conversation")
    return {"status": "success"}


# --- Timeline ---
@router.get("/{workspace_id}/timeline")
async def get_timeline(
    workspace_id: int, owner_info: tuple[OwnerType, str] = Depends(resolve_owner), db: AsyncSession = Depends(get_db)
):
    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    activities = await service.get_timeline(workspace_id, owner_type.value, owner_id)

    return [
        {
            "id": a.id,
            "event_type": a.event_type,
            "actor_type": a.actor_type,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "metadata": a.metadata_payload,
            "created_at": a.created_at,
        }
        for a in activities
    ]


# --- Digests ---
@router.get("/{workspace_id}/digests")
async def get_digests(
    workspace_id: int, owner_info: tuple[OwnerType, str] = Depends(resolve_owner), db: AsyncSession = Depends(get_db)
):
    from app.ai.chat.digest_service import DigestService

    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    ws = await service.get_workspace(workspace_id, owner_type.value, owner_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    digest_service = DigestService(db)
    digests = await digest_service.list_digests(workspace_id)

    return [
        {
            "id": d.id,
            "since_time": d.since_time,
            "until_time": d.until_time,
            "status": d.status,
            "metadata_payload": d.metadata_payload,
            "created_at": d.created_at,
            "summary": d.summary,
        }
        for d in digests
    ]


@router.get("/{workspace_id}/digests/{digest_id}")
async def get_digest(
    workspace_id: int,
    digest_id: int,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    from app.models.workspace import WorkspaceDigest

    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    ws = await service.get_workspace(workspace_id, owner_type.value, owner_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    stmt = select(WorkspaceDigest).where(WorkspaceDigest.id == digest_id, WorkspaceDigest.workspace_id == workspace_id)
    res = await db.execute(stmt)
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Digest not found")

    return {
        "id": d.id,
        "since_time": d.since_time,
        "until_time": d.until_time,
        "status": d.status,
        "metadata_payload": d.metadata_payload,
        "created_at": d.created_at,
        "content": d.content,
        "summary": d.summary,
    }


class GenerateDigestRequest(BaseModel):
    since_time: datetime | None = None


@router.post("/{workspace_id}/digests")
async def generate_digest(
    workspace_id: int,
    body: GenerateDigestRequest,
    owner_info: tuple[OwnerType, str] = Depends(resolve_owner),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta, timezone

    from app.ai.chat.digest_service import DigestService

    owner_type, owner_id = owner_info
    service = WorkspaceService(db)
    ws = await service.get_workspace(workspace_id, owner_type.value, owner_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    digest_service = DigestService(db)

    since_time = body.since_time
    if not since_time:
        # Default to last digest time or 24 hours ago
        latest = await digest_service.get_latest_digest(workspace_id)
        if latest:
            since_time = latest.until_time
        else:
            since_time = datetime.now(timezone.utc) - timedelta(days=1)

    until_time = datetime.now(timezone.utc)

    generator = digest_service.generate_digest_stream(workspace_id, since_time, until_time)
    return StreamingResponse(generator, media_type="text/event-stream")
