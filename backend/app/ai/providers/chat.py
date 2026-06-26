from collections.abc import AsyncGenerator

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str # system, user, assistant, tool
    content: str
    name: str | None = None

class StreamChunk(BaseModel):
    chunk_text: str
    finish_reason: str | None = None
    usage: dict[str, int] | None = None

class ChatProvider:
    """
    Interface for conversational LLM generation.
    Strictly separated from BaseAIProvider which is for discrete AI tasks (extraction, summary).
    """
    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    def default_model(self) -> str:
        raise NotImplementedError

    def supports_tools(self) -> bool:
        return False

    def supports_json(self) -> bool:
        return False

    def supports_vision(self) -> bool:
        return False

    async def generate(self, messages: list[ChatMessage], model: str | None = None, **kwargs) -> str:
        """Non-streaming generation."""
        raise NotImplementedError

    async def generate_stream(self, messages: list[ChatMessage], model: str | None = None, **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """Streaming generation."""
        raise NotImplementedError

    async def count_tokens(self, messages: list[ChatMessage], model: str | None = None) -> int:
        """Estimate token usage before generation."""
        raise NotImplementedError
