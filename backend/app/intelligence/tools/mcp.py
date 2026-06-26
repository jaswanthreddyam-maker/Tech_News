from typing import Any

from app.intelligence.mcp.transport import MCPConnection
from app.intelligence.tools.base import ToolProvider


class MCPToolProvider(ToolProvider):
    """
    Exposes tools fetched from an active remote MCP connection.
    """
    def __init__(self, connection: MCPConnection):
        self.connection = connection

    @property
    def provider_name(self) -> str:
        return f"mcp_{self.connection.name}"

    async def get_tools(self) -> list[dict[str, Any]]:
        # Fetch the tools directly from the MCP Server
        return await self.connection.list_tools()

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        # Execute the tool remotely
        return await self.connection.call_tool(name, arguments)
