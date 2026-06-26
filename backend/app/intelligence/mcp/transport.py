from typing import Any


class MCPTransport:
    """
    Interface for the underlying MCP protocol transport layer (Stdio, SSE, etc.)
    """
    async def connect(self):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError

    async def send_request(self, method: str, params: dict[str, Any]) -> Any:
        raise NotImplementedError

class StdioTransport(MCPTransport):
    """
    Stub for the standard I/O MCP transport.
    """
    def __init__(self, command: str, args: list[str]):
        self.command = command
        self.args = args

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def send_request(self, method: str, params: dict[str, Any]) -> Any:
        # Mock responses based on method for Sprint 5 testing
        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "mcp_search_web",
                        "description": "Searches the web via MCP",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"]
                        }
                    }
                ]
            }
        elif method == "tools/call":
            return {"content": [{"type": "text", "text": "Mock web search result from MCP"}]}
        return {}

class MCPConnection:
    """
    High-level wrapper around the transport, providing typed MCP operations.
    """
    def __init__(self, name: str, transport: MCPTransport):
        self.name = name
        self.transport = transport

    async def connect(self):
        await self.transport.connect()

    async def disconnect(self):
        await self.transport.disconnect()

    async def list_tools(self) -> list[dict[str, Any]]:
        response = await self.transport.send_request("tools/list", {})
        return response.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        response = await self.transport.send_request("tools/call", {"name": name, "arguments": arguments})
        return response
