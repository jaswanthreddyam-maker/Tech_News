from typing import Any

from app.intelligence.tools.base import ToolProvider


class ToolRegistry:
    """
    Unified facade combining Local and MCP Tool Providers.
    The GenerationPipeline queries this registry to get a flattened list of tools.
    """
    def __init__(self):
        self._providers: dict[str, ToolProvider] = {}
        # Map of tool_name -> provider_name to route executions
        self._tool_routes: dict[str, str] = {}

    def register_provider(self, provider: ToolProvider):
        self._providers[provider.provider_name] = provider

    async def get_all_tools(self) -> list[dict[str, Any]]:
        all_tools = []
        # Rebuild routing map to ensure it's fresh
        self._tool_routes.clear()

        for provider_name, provider in self._providers.items():
            tools = await provider.get_tools()
            for t in tools:
                tool_name = t.get("name")
                if not isinstance(tool_name, str):
                    continue
                # Very basic conflict resolution: first one wins or prefix it
                # For Sprint 5 we'll just overwrite or assume no overlap, but normally
                # we'd namespace: f"{provider_name}_{tool_name}" if conflicts exist.
                self._tool_routes[tool_name] = provider_name
                all_tools.append(t)

        return all_tools

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._tool_routes:
            raise KeyError(f"Tool {name} not found in ToolRegistry routing map. Did you call get_all_tools() first?")

        provider_name = self._tool_routes[name]
        provider = self._providers[provider_name]

        return await provider.execute_tool(name, arguments)
