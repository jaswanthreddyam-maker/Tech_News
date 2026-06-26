from typing import Any, Protocol


class Planner(Protocol):
    """Stub for Agentic Planning Stage"""
    async def generate_plan(self, context: Any) -> Any: ...

class MemoryProvider(Protocol):
    """Retrieves conversation, workspace, or entity memory"""
    async def load_memory(self, context: Any) -> Any: ...

class ToolProvider(Protocol):
    """Registry for MCP, REST, Internal Tools"""
    @property
    def provider_type(self) -> str: ... # INTERNAL, MCP, REST
    async def execute_tool(self, tool_name: str, args: dict[str, Any]) -> Any: ...

class InputValidator(Protocol):
    """Guardrails before processing (PII, Prompt Injection)"""
    def validate(self, context: Any) -> bool: ...

class OutputValidator(Protocol):
    """Post-generation guardrails (Citation, JSON, Hallucination)"""
    def execute(self, response_text: str, context: Any) -> dict[str, Any]: ...

class RecoveryStrategy(Protocol):
    """Defines how to recover from generation failures (Retry, Fallback, Cached)"""
    async def recover(self, exception: Exception, context: Any) -> Any: ...
