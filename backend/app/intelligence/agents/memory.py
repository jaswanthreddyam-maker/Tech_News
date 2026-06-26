from typing import Any


class MemoryProvider:
    """
    Base interface for fetching and storing stateful memory contexts.
    """
    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    async def load_memory(self, context: Any) -> None:
        raise NotImplementedError

    async def save_memory(self, context: Any, response: Any) -> None:
        raise NotImplementedError

class ConversationMemory(MemoryProvider):
    @property
    def provider_name(self) -> str:
        return "ConversationMemory"

    async def load_memory(self, context: Any) -> None:
        # Fetch multi-turn conversation history
        pass

    async def save_memory(self, context: Any, response: Any) -> None:
        pass

class WorkspaceMemory(MemoryProvider):
    @property
    def provider_name(self) -> str:
        return "WorkspaceMemory"

    async def load_memory(self, context: Any) -> None:
        pass

    async def save_memory(self, context: Any, response: Any) -> None:
        pass

class EntityMemory(MemoryProvider):
    @property
    def provider_name(self) -> str: return "EntityMemory"
    async def load_memory(self, context: Any) -> None: pass
    async def save_memory(self, context: Any, response: Any) -> None: pass

class VectorMemory(MemoryProvider):
    @property
    def provider_name(self) -> str: return "VectorMemory"
    async def load_memory(self, context: Any) -> None: pass
    async def save_memory(self, context: Any, response: Any) -> None: pass

class LongTermMemory(MemoryProvider):
    @property
    def provider_name(self) -> str: return "LongTermMemory"
    async def load_memory(self, context: Any) -> None: pass
    async def save_memory(self, context: Any, response: Any) -> None: pass

class ExternalMemory(MemoryProvider):
    @property
    def provider_name(self) -> str: return "ExternalMemory"
    async def load_memory(self, context: Any) -> None: pass
    async def save_memory(self, context: Any, response: Any) -> None: pass

class MemoryRegistry:
    def __init__(self):
        self._providers: dict[str, MemoryProvider] = {}

    def register(self, provider: MemoryProvider):
        self._providers[provider.provider_name] = provider

    def get(self, name: str) -> MemoryProvider:
        if name not in self._providers:
            raise KeyError(f"Memory Provider {name} not found.")
        return self._providers[name]
