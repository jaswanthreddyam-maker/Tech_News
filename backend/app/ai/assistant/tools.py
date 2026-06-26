import json
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


class Tool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]

    # We use a callable that takes kwargs and returns a string (the tool result)
    # The actual implementation of execute is separated from the model
    # but we can store it in the registry.


class AssistantToolRegistry:
    """
    Registry for tools available to the Personal AI Assistant.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._executors: dict[str, Callable[..., Awaitable[str]]] = {}

    def register(self, tool: Tool, executor: Callable[..., Awaitable[str]]):
        self._tools[tool.name] = tool
        self._executors[tool.name] = executor

    def get_all_tools_schema(self) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in self._tools.values()
        ]

    async def execute_tool(
        self, name: str, kwargs: dict[str, Any], db: AsyncSession, owner_type: str, owner_id: str
    ) -> str:
        if name not in self._executors:
            return f"Error: Tool '{name}' not found."

        try:
            # We inject contextual kwargs that tools might need
            kwargs["db"] = db
            kwargs["owner_type"] = owner_type
            kwargs["owner_id"] = owner_id

            result = await self._executors[name](**kwargs)
            if not isinstance(result, str):
                result = json.dumps(result, default=str)
            return result
        except Exception as e:
            return f"Error executing tool '{name}': {e!s}"
