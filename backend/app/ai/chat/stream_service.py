from collections.abc import AsyncGenerator
from typing import Any

from app.ai.chat.schemas import StreamEvent, StreamEventType


class StreamService:
    """
    Formats events into Server-Sent Events (SSE) compliant strings.
    Protocol:
    data: {"event": "retrieval_started", "data": {}}
    data: {"event": "token", "data": {"text": "Hello"}}
    """

    @staticmethod
    def format_sse(event: StreamEventType, data: dict[str, Any]) -> str:
        payload = StreamEvent(event=event, data=data)
        return f"data: {payload.model_dump_json()}\n\n"

    @staticmethod
    async def stream_tokens(token_generator: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """Takes an async generator of raw string tokens and formats them as SSE events."""
        async for token in token_generator:
            yield StreamService.format_sse(StreamEventType.TOKEN, {"text": token})

    @staticmethod
    def format_error(message: str) -> str:
        return StreamService.format_sse(StreamEventType.ERROR, {"message": message})
