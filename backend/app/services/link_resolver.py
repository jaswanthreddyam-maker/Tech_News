import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import WorkspaceNote


class LinkResolver:
    """Base class for resolving wiki links inside content."""

    async def resolve(self, workspace_id: int, identifier: str) -> dict[str, Any] | None:
        raise NotImplementedError


class NoteResolver(LinkResolver):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(self, workspace_id: int, identifier: str) -> dict[str, Any] | None:
        # Resolve by note title
        stmt = (
            select(WorkspaceNote)
            .where(WorkspaceNote.workspace_id == workspace_id, WorkspaceNote.title.ilike(identifier))
            .limit(1)
        )
        res = await self.db.execute(stmt)
        note = res.scalars().first()
        if note:
            return {"id": note.id, "title": note.title, "type": "note"}
        return None


class DynamicBacklinkResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_backlinks(self, workspace_id: int, note_id: int) -> list[dict[str, Any]]:
        # Fetch the target note to get its title
        stmt = select(WorkspaceNote).where(WorkspaceNote.id == note_id, WorkspaceNote.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        target_note = res.scalars().first()
        if not target_note or not target_note.title:
            return []

        title = target_note.title
        # Find any other note in the same workspace that references this title in a wiki link
        # e.g. [[Title]] or [[Title|Alias]]
        search_pattern = f"%[[{title}]]%"
        alias_pattern = f"%[[{title}|%"

        stmt_backlinks = select(WorkspaceNote).where(
            WorkspaceNote.workspace_id == workspace_id,
            WorkspaceNote.id != note_id,
            (WorkspaceNote.content.ilike(search_pattern) | WorkspaceNote.content.ilike(alias_pattern)),
        )
        res_backlinks = await self.db.execute(stmt_backlinks)
        referencing_notes = res_backlinks.scalars().all()

        backlinks = []
        # Extract a small excerpt of context where the reference happens
        pattern = re.compile(rf"\[\[({re.escape(title)})(?:\|.*?)?\]\]", re.IGNORECASE)

        for ref_note in referencing_notes:
            content = ref_note.content or ""
            match = pattern.search(content)
            excerpt = ""
            if match:
                start = max(0, match.start() - 40)
                end = min(len(content), match.end() + 40)
                excerpt = "..." + content[start:end].replace("\n", " ").strip() + "..."

            backlinks.append({"id": ref_note.id, "title": ref_note.title, "excerpt": excerpt})

        return backlinks
