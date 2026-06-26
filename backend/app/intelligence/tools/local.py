from collections.abc import Callable
from typing import Any

from app.intelligence.tools.base import ToolProvider


class LocalToolProvider(ToolProvider):
    """
    Provides native Python functions wrapped as AI tools.
    """
    def __init__(self, provider_name: str = "local"):
        self._provider_name = provider_name
        self.tools: dict[str, dict[str, Any]] = {}
        self.callbacks: dict[str, Callable] = {}

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def register_tool(self, definition: dict[str, Any], callback: Callable):
        name = definition.get("name")
        if not isinstance(name, str):
            raise ValueError("Tool definition must have a string 'name'")
        self.tools[name] = definition
        self.callbacks[name] = callback

    async def get_tools(self) -> list[dict[str, Any]]:
        return list(self.tools.values())

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self.callbacks:
            raise KeyError(f"Tool {name} not found in {self.provider_name}")

        import inspect
        callback = self.callbacks[name]

        if inspect.iscoroutinefunction(callback):
            return await callback(**arguments)
        else:
            return callback(**arguments)
