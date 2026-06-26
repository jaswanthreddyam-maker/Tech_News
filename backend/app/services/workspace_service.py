import logging

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workspace import (
    NoteChangeType,
    Workspace,
    WorkspaceActivity,
    WorkspaceArticle,
    WorkspaceConversation,
    WorkspaceEventType,
    WorkspaceNote,
    WorkspaceNoteVersion,
)
from app.services.activity_logger import ActivityLogger

logger = logging.getLogger("tech_news.services.workspace_service")


class WorkspaceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workspace(
        self, owner_type: str, owner_id: str, name: str, description: str | None = None
    ) -> Workspace:
        workspace = Workspace(owner_type=owner_type, owner_id=owner_id, name=name, description=description)
        self.db.add(workspace)
        await self.db.flush()

        await ActivityLogger.log(
            self.db,
            workspace_id=workspace.id,
            event_type=WorkspaceEventType.WORKSPACE_CREATED,
            actor_type=owner_type,
            resource_type="workspace",
            metadata={"name": name},
        )

        await self.db.commit()
        await self.db.refresh(workspace)

        return workspace

    async def get_workspace(self, workspace_id: int, owner_type: str, owner_id: str) -> Workspace | None:
        stmt = (
            select(Workspace)
            .options(
                selectinload(Workspace.articles).selectinload(WorkspaceArticle.article),
                selectinload(Workspace.conversations),
                selectinload(Workspace.notes),
            )
            .where(
                and_(Workspace.id == workspace_id, Workspace.owner_type == owner_type, Workspace.owner_id == owner_id)
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_workspaces(self, owner_type: str, owner_id: str) -> list[Workspace]:
        stmt = (
            select(Workspace)
            .where(and_(Workspace.owner_type == owner_type, Workspace.owner_id == owner_id))
            .order_by(Workspace.updated_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def rename_workspace(
        self, workspace_id: int, owner_type: str, owner_id: str, new_name: str
    ) -> Workspace | None:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return None
        workspace.name = new_name

        await ActivityLogger.log(
            self.db,
            workspace_id=workspace.id,
            event_type=WorkspaceEventType.WORKSPACE_RENAMED,
            actor_type=owner_type,
            resource_type="workspace",
            metadata={"new_name": new_name},
        )

        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def delete_workspace(self, workspace_id: int, owner_type: str, owner_id: str) -> bool:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return False
        await self.db.delete(workspace)
        await self.db.commit()
        return True

    # --- Pinned Articles ---
    async def pin_article(
        self, workspace_id: int, owner_type: str, owner_id: str, article_id: int
    ) -> WorkspaceArticle | None:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return None

        # Check if already pinned
        stmt = select(WorkspaceArticle).where(
            and_(WorkspaceArticle.workspace_id == workspace_id, WorkspaceArticle.article_id == article_id)
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            return None

        wa = WorkspaceArticle(workspace_id=workspace_id, article_id=article_id)
        self.db.add(wa)

        await ActivityLogger.log(
            self.db,
            workspace_id=workspace_id,
            event_type=WorkspaceEventType.ARTICLE_PINNED,
            actor_type=owner_type,
            resource_type="article",
            resource_id=str(article_id),
            metadata={"article_id": article_id},
        )

        await self.db.commit()
        await self.db.refresh(wa)
        return wa

    async def unpin_article(self, workspace_id: int, owner_type: str, owner_id: str, article_id: int) -> bool:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return False

        stmt = delete(WorkspaceArticle).where(
            and_(WorkspaceArticle.workspace_id == workspace_id, WorkspaceArticle.article_id == article_id)
        )
        await self.db.execute(stmt)

        await ActivityLogger.log(
            self.db,
            workspace_id=workspace_id,
            event_type=WorkspaceEventType.ARTICLE_UNPINNED,
            actor_type=owner_type,
            resource_type="article",
            resource_id=str(article_id),
            metadata={"article_id": article_id},
        )

        await self.db.commit()
        return True

    # --- Conversations ---
    async def attach_conversation(
        self, workspace_id: int, owner_type: str, owner_id: str, conversation_id: str
    ) -> WorkspaceConversation | None:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return None

        stmt = select(WorkspaceConversation).where(
            and_(
                WorkspaceConversation.workspace_id == workspace_id,
                WorkspaceConversation.conversation_id == conversation_id,
            )
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            return None

        wc = WorkspaceConversation(workspace_id=workspace_id, conversation_id=conversation_id)
        self.db.add(wc)

        await ActivityLogger.log(
            self.db,
            workspace_id=workspace_id,
            event_type=WorkspaceEventType.CHAT_STARTED,
            actor_type=owner_type,
            resource_type="conversation",
            resource_id=conversation_id,
        )

        await self.db.commit()
        await self.db.refresh(wc)
        return wc

    # --- Notes ---
    async def add_note(self, workspace_id: int, owner_type: str, owner_id: str, content: str) -> WorkspaceNote | None:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return None

        wn = WorkspaceNote(workspace_id=workspace_id, title=content[:20] + "...", content=content, version_number=1)
        self.db.add(wn)
        await self.db.flush()

        wnv = WorkspaceNoteVersion(
            note_id=wn.id,
            version_number=wn.version_number,
            content=wn.content,
            change_type=NoteChangeType.MANUAL,
            created_by=owner_type,
        )
        self.db.add(wnv)

        await ActivityLogger.log(
            self.db,
            workspace_id=workspace_id,
            event_type=WorkspaceEventType.NOTE_CREATED,
            actor_type=owner_type,
            resource_type="note",
            metadata={"content_preview": content[:50]},
        )

        await self.db.commit()
        await self.db.refresh(wn)

        # Trigger embedding in background
        from celery_app import celery_app as celery

        celery.send_task("tasks.ai.process_note_embedding_task", args=[wn.id])

        return wn

    async def update_note(
        self,
        workspace_id: int,
        owner_type: str,
        owner_id: str,
        note_id: int,
        content: str,
        title: str | None = None,
        summary: str | None = None,
        change_type: str = NoteChangeType.MANUAL,
        created_by: str | None = None,
    ) -> WorkspaceNote | None:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return None

        stmt = select(WorkspaceNote).where(
            and_(WorkspaceNote.id == note_id, WorkspaceNote.workspace_id == workspace_id)
        )
        res = await self.db.execute(stmt)
        note = res.scalars().first()
        if not note:
            return None

        note.content = content
        if title is not None:
            note.title = title
        if summary is not None:
            note.summary = summary

        note.version_number += 1

        if created_by == "ai":
            from datetime import datetime, timezone

            note.last_ai_modified_at = datetime.now(timezone.utc)

        wnv = WorkspaceNoteVersion(
            note_id=note.id,
            version_number=note.version_number,
            content=note.content,
            summary=note.summary,
            change_type=change_type,
            created_by=created_by or owner_type,
        )
        self.db.add(wnv)

        await ActivityLogger.log(
            self.db,
            workspace_id=workspace_id,
            event_type=WorkspaceEventType.NOTE_UPDATED,
            actor_type=owner_type,
            resource_type="note",
            resource_id=str(note.id),
        )

        await self.db.commit()
        await self.db.refresh(note)

        # Trigger embedding in background
        from celery_app import celery_app as celery

        celery.send_task("tasks.ai.process_note_embedding_task", args=[note.id])

        return note

    async def delete_note(self, workspace_id: int, owner_type: str, owner_id: str, note_id: int) -> bool:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return False

        stmt = delete(WorkspaceNote).where(
            and_(WorkspaceNote.id == note_id, WorkspaceNote.workspace_id == workspace_id)
        )
        await self.db.execute(stmt)

        await ActivityLogger.log(
            self.db,
            workspace_id=workspace_id,
            event_type=WorkspaceEventType.NOTE_DELETED,
            actor_type=owner_type,
            resource_type="note",
            resource_id=str(note_id),
        )

        await self.db.commit()
        return True

    async def get_note_versions(
        self, workspace_id: int, owner_type: str, owner_id: str, note_id: int
    ) -> list[WorkspaceNoteVersion]:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return []

        stmt = (
            select(WorkspaceNoteVersion)
            .where(WorkspaceNoteVersion.note_id == note_id)
            .order_by(WorkspaceNoteVersion.version_number.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def restore_note_version(
        self, workspace_id: int, owner_type: str, owner_id: str, note_id: int, version_number: int
    ) -> WorkspaceNote | None:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return None

        stmt = select(WorkspaceNoteVersion).where(
            and_(WorkspaceNoteVersion.note_id == note_id, WorkspaceNoteVersion.version_number == version_number)
        )
        res = await self.db.execute(stmt)
        version = res.scalars().first()
        if not version:
            return None

        return await self.update_note(
            workspace_id=workspace_id,
            owner_type=owner_type,
            owner_id=owner_id,
            note_id=note_id,
            content=version.content,
            summary=version.summary,
            change_type=NoteChangeType.RESTORE,
            created_by=owner_type,
        )

    async def get_timeline(
        self, workspace_id: int, owner_type: str, owner_id: str, limit: int = 50
    ) -> list[WorkspaceActivity]:
        workspace = await self.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return []

        stmt = (
            select(WorkspaceActivity)
            .where(WorkspaceActivity.workspace_id == workspace_id)
            .order_by(WorkspaceActivity.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
