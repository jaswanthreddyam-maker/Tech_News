import json
import logging
from datetime import timedelta

from app.ai.chat.schemas import ChatMessage
from app.core.redis import get_redis_client

logger = logging.getLogger("tech_news.ai.chat.memory")


class MemoryManager:
    """
    Manages conversational memory in Redis.
    Strategy: Store up to N recent messages. When exceeding N, trigger a summarization
    of the oldest messages and store it separately.

    Keys:
    - chat:{session_id}:messages (List of JSON) -> TTL 7 days
    - chat:{session_id}:summary (String) -> TTL 30 days
    """

    def __init__(self, recent_limit: int = 6):
        self.recent_limit = recent_limit
        self.msg_ttl = timedelta(days=7)
        self.summary_ttl = timedelta(days=30)
        self.redis = get_redis_client()

    def _msg_key(self, session_id: str) -> str:
        return f"chat:{session_id}:messages"

    def _summary_key(self, session_id: str) -> str:
        return f"chat:{session_id}:summary"

    async def get_context(self, session_id: str) -> tuple[list[ChatMessage], str | None]:
        """Returns the recent messages and the current conversation summary."""
        if not self.redis:
            return [], None

        messages_json = await self.redis.lrange(self._msg_key(session_id), 0, -1)
        summary = await self.redis.get(self._summary_key(session_id))

        messages = [ChatMessage.model_validate(json.loads(m)) for m in messages_json]
        summary_str = summary.decode("utf-8") if isinstance(summary, bytes) else summary

        return messages, summary_str

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Adds a message to the session. If over limit, we don't summarize here, we just append.
        Summarization should be triggered by the ConversationService asynchronously to not block user."""
        if not self.redis:
            return

        key = self._msg_key(session_id)
        await self.redis.rpush(key, message.model_dump_json())
        await self.redis.expire(key, int(self.msg_ttl.total_seconds()))

    async def get_messages_for_summarization(self, session_id: str) -> list[ChatMessage]:
        """Returns messages that exceed the recent_limit to be summarized."""
        if not self.redis:
            return []

        len_msgs = await self.redis.llen(self._msg_key(session_id))
        if len_msgs <= self.recent_limit:
            return []

        # Get all messages except the last `recent_limit`
        to_summarize_count = len_msgs - self.recent_limit
        messages_json = await self.redis.lrange(self._msg_key(session_id), 0, to_summarize_count - 1)
        return [ChatMessage.model_validate(json.loads(m)) for m in messages_json]

    async def commit_summary(self, session_id: str, new_summary: str, pruned_count: int) -> None:
        """Saves the new summary and drops the oldest `pruned_count` messages."""
        if not self.redis:
            return

        key = self._msg_key(session_id)
        summary_key = self._summary_key(session_id)

        # Trim the list: keep only from `pruned_count` to the end
        await self.redis.ltrim(key, pruned_count, -1)

        # Save new summary
        await self.redis.setex(summary_key, int(self.summary_ttl.total_seconds()), new_summary)
