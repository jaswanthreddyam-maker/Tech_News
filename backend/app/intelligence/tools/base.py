from typing import Any


class ToolProvider:
    """
    Interface for providing tools to the Registry.
    Could be backed by native code (Local) or a remote protocol (MCP).
    """
    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    async def get_tools(self) -> list[dict[str, Any]]:
        """Returns tool definitions in OpenAI/JSON Schema format."""
        raise NotImplementedError

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Executes the tool and returns the result."""
        raise NotImplementedError
