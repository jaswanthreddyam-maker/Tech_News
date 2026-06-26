import pytest

from app.intelligence.mcp.transport import MCPConnection, StdioTransport
from app.intelligence.tools.local import LocalToolProvider
from app.intelligence.tools.mcp import MCPToolProvider
from app.intelligence.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_tool_registry_federation():
    # 1. Setup Local Provider
    local_provider = LocalToolProvider()
    local_provider.register_tool(
        definition={
            "name": "local_extract",
            "description": "Extracts entities locally",
            "inputSchema": {"type": "object", "properties": {}}
        },
        callback=lambda: "Local result"
    )

    # 2. Setup Mock MCP Provider
    transport = StdioTransport("mock", [])
    connection = MCPConnection("test_server", transport)
    mcp_provider = MCPToolProvider(connection)

    # 3. Setup Registry
    registry = ToolRegistry()
    registry.register_provider(local_provider)
    registry.register_provider(mcp_provider)

    # 4. Fetch all tools
    all_tools = await registry.get_all_tools()

    # We expect 1 from local and 1 from the StdioTransport mock ("mcp_search_web")
    assert len(all_tools) == 2
    tool_names = [t.get("name") for t in all_tools]
    assert "local_extract" in tool_names
    assert "mcp_search_web" in tool_names

    # 5. Execute tools
    local_res = await registry.execute_tool("local_extract", {})
    assert local_res == "Local result"

    mcp_res = await registry.execute_tool("mcp_search_web", {"query": "tech news"})
    assert "Mock web search" in mcp_res["content"][0]["text"]
