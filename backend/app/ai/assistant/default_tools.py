import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.assistant.tools import AssistantToolRegistry, Tool
from app.ai.chat.digest_service import DigestService
from app.services.workspace_service import WorkspaceService


async def list_workspaces_executor(db: AsyncSession, owner_type: str, owner_id: str, **kwargs) -> str:
    service = WorkspaceService(db)
    wses = await service.list_workspaces(owner_type, owner_id)
    if not wses:
        return "You have no workspaces."
    res = []
    for w in wses:
        res.append({"id": w.id, "name": w.name, "description": w.description, "created_at": w.created_at.isoformat()})
    return json.dumps(res, indent=2)


async def recent_activity_executor(
    workspace_id: int, db: AsyncSession, owner_type: str, owner_id: str, **kwargs
) -> str:
    service = WorkspaceService(db)
    timeline = await service.get_timeline(workspace_id, owner_type, owner_id)
    if not timeline:
        return f"No recent activity in workspace {workspace_id}."
    res = []
    for t in timeline[:20]:
        res.append(f"[{t.created_at.isoformat()}] {t.event_type}: {t.resource_type} {t.resource_id}")
    return "\n".join(res)


async def search_my_knowledge_executor(
    query: str, workspace_id: int | None, db: AsyncSession, owner_type: str, owner_id: str, **kwargs
) -> str:
    # A generic semantic search across all or one workspace
    # Since search_notes is workspace scoped, we need to iterate if workspace_id is None
    service = WorkspaceService(db)

    workspaces = []
    if workspace_id:
        w = await service.get_workspace(workspace_id, owner_type, owner_id)
        if w:
            workspaces.append(w)
    else:
        workspaces = await service.list_workspaces(owner_type, owner_id)

    results = []
    for w in workspaces:
        notes = await service.search_notes(w.id, query)
        for n in notes:
            results.append(f"Workspace '{w.name}': Note '{n.get('title')}' -> {n.get('summary') or n.get('content')}")

    if not results:
        return "No knowledge found for the query."

    return "\n".join(results[:10])


async def read_digests_executor(workspace_id: int, db: AsyncSession, owner_type: str, owner_id: str, **kwargs) -> str:
    service = DigestService(db)
    digests = await service.list_digests(workspace_id)
    if not digests:
        return f"No daily digests available in workspace {workspace_id}."

    res = []
    for d in digests[:3]:
        res.append(f"--- Digest {d.created_at.isoformat()} ---\n{d.content}\n")
    return "\n".join(res)


async def read_note_executor(
    workspace_id: int, note_id: int, db: AsyncSession, owner_type: str, owner_id: str, **kwargs
) -> str:
    service = WorkspaceService(db)
    ws = await service.get_workspace(workspace_id, owner_type, owner_id)
    if not ws:
        return "Workspace not found."
    for n in ws.notes:
        if n.id == note_id:
            return f"Note Title: {n.title}\nNote Content:\n{n.content}"
    return "Note not found."


def register_default_tools(registry: AssistantToolRegistry):
    registry.register(
        Tool(
            name="list_workspaces",
            description="Returns a list of all your research workspaces, including their ID, name, and description.",
            parameters={"type": "object", "properties": {}, "required": []},
        ),
        list_workspaces_executor,
    )

    registry.register(
        Tool(
            name="recent_activity",
            description="Returns the recent timeline of activity (notes, articles pinned, conversations) in a specific workspace.",
            parameters={
                "type": "object",
                "properties": {"workspace_id": {"type": "integer", "description": "The ID of the workspace to check"}},
                "required": ["workspace_id"],
            },
        ),
        recent_activity_executor,
    )

    registry.register(
        Tool(
            name="search_my_knowledge",
            description="Performs semantic search across your personal notes and summaries to find information you have saved.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The question or topic to search for in your notes."},
                    "workspace_id": {
                        "type": "integer",
                        "description": "Optional ID of a specific workspace to limit the search. Leave null to search all workspaces.",
                    },
                },
                "required": ["query"],
            },
        ),
        search_my_knowledge_executor,
    )

    registry.register(
        Tool(
            name="read_digests",
            description="Fetches recent daily digests for a workspace, useful for finding what changed recently.",
            parameters={
                "type": "object",
                "properties": {"workspace_id": {"type": "integer", "description": "The ID of the workspace."}},
                "required": ["workspace_id"],
            },
        ),
        read_digests_executor,
    )

    registry.register(
        Tool(
            name="read_note",
            description="Reads the full text content of a specific note.",
            parameters={
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "integer", "description": "The ID of the workspace containing the note."},
                    "note_id": {"type": "integer", "description": "The ID of the note."},
                },
                "required": ["workspace_id", "note_id"],
            },
        ),
        read_note_executor,
    )
