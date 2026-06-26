from app.intelligence.mcp.transport import MCPConnection


class MCPProvider:
    """
    Manages multiple active MCP connections.
    """
    def __init__(self):
        self.connections: dict[str, MCPConnection] = {}

    def register_connection(self, connection: MCPConnection):
        self.connections[connection.name] = connection

    async def connect_all(self):
        for conn in self.connections.values():
            await conn.connect()

    async def disconnect_all(self):
        for conn in self.connections.values():
            await conn.disconnect()

    def get_connection(self, name: str) -> MCPConnection:
        if name not in self.connections:
            raise KeyError(f"MCP Connection {name} not found")
        return self.connections[name]
