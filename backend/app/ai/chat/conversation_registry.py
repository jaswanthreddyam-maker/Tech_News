import logging
from datetime import datetime, timedelta, timezone

from app.ai.chat.schemas import ConversationMetadata, ConversationMode, OwnerType
from app.core.redis import get_redis_client

logger = logging.getLogger("tech_news.ai.chat.conversation_registry")


class ConversationRegistry:
    """
    Manages conversation lifecycle: create, rename, delete, list, ownership.
    Separated from ConversationService to keep orchestration focused on RAG.

    Redis Keys:
    - owner:{owner_type}:{owner_id}:conversations  (Sorted Set, score=updated_at timestamp)
    - chat:{conversation_id}:metadata               (Hash)
    """

    def __init__(self):
        self.redis = get_redis_client()
        self.metadata_ttl = timedelta(days=30)

    def _owner_key(self, owner_type: str, owner_id: str) -> str:
        return f"owner:{owner_type}:{owner_id}:conversations"

    def _meta_key(self, conversation_id: str) -> str:
        return f"chat:{conversation_id}:metadata"

    def _serialize_metadata(self, data: dict) -> dict[str, str]:
        """Serializes metadata for Redis by omitting None values and stringifying the rest."""
        return {
            k: str(v) if not isinstance(v, str) else v
            for k, v in data.items()
            if v is not None
        }

    async def create(
        self,
        conversation_id: str,
        owner_type: OwnerType,
        owner_id: str,
        mode: ConversationMode = ConversationMode.GENERAL,
        article_id: int | None = None,
        workspace_id: int | None = None,
    ) -> ConversationMetadata:
        """Creates a new conversation and registers it under the owner."""
        if not self.redis:
            return ConversationMetadata(conversation_id=conversation_id)

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        now_ts = now.timestamp()

        meta = ConversationMetadata(
            conversation_id=conversation_id,
            title="New Conversation",
            mode=mode,
            owner_type=owner_type,
            owner_id=owner_id,
            article_id=article_id,
            workspace_id=workspace_id,
            message_count=0,
            last_model="",
            created_at=now_iso,
            updated_at=now_iso,
        )

        # Store metadata hash
        meta_key = self._meta_key(conversation_id)
        mapping = self._serialize_metadata(meta.model_dump(mode="json"))
        await self.redis.hset(meta_key, mapping=mapping)
        await self.redis.expire(meta_key, int(self.metadata_ttl.total_seconds()))

        # Register in owner's sorted set
        owner_key = self._owner_key(owner_type.value, owner_id)
        await self.redis.zadd(owner_key, {conversation_id: now_ts})
        await self.redis.expire(owner_key, int(self.metadata_ttl.total_seconds()))

        logger.info(f"Created conversation {conversation_id} for {owner_type.value}:{owner_id}")
        return meta

    async def get(self, conversation_id: str) -> ConversationMetadata | None:
        """Retrieves metadata for a conversation."""
        if not self.redis:
            return None

        meta_key = self._meta_key(conversation_id)
        data = await self.redis.hgetall(meta_key)
        if not data:
            return None

        # Redis returns bytes keys/values
        decoded = {
            (k.decode("utf-8") if isinstance(k, bytes) else k): (v.decode("utf-8") if isinstance(v, bytes) else v)
            for k, v in data.items()
        }
        return ConversationMetadata.model_validate(decoded)

    async def rename(self, conversation_id: str, new_title: str) -> bool:
        """Renames a conversation."""
        if not self.redis:
            return False

        meta_key = self._meta_key(conversation_id)
        exists = await self.redis.exists(meta_key)
        if not exists:
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        await self.redis.hset(meta_key, mapping={"title": new_title, "updated_at": now_iso})
        return True

    async def delete(self, conversation_id: str) -> bool:
        """Deletes a conversation: metadata, messages, summary, and owner index entry."""
        if not self.redis:
            return False

        meta = await self.get(conversation_id)
        if not meta:
            return False

        # Remove from owner's sorted set
        owner_key = self._owner_key(meta.owner_type, meta.owner_id)
        await self.redis.zrem(owner_key, conversation_id)

        # Delete all conversation keys
        keys_to_delete = [
            self._meta_key(conversation_id),
            f"chat:{conversation_id}:messages",
            f"chat:{conversation_id}:summary",
        ]
        await self.redis.delete(*keys_to_delete)

        logger.info(f"Deleted conversation {conversation_id}")
        return True

    async def list_conversations(
        self,
        owner_type: OwnerType,
        owner_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationMetadata]:
        """Lists conversations for an owner, most recent first."""
        if not self.redis:
            return []

        owner_key = self._owner_key(owner_type.value, owner_id)

        # Get conversation IDs sorted by recency (descending)
        conv_ids_bytes = await self.redis.zrevrange(owner_key, offset, offset + limit - 1)
        conv_ids = [cid.decode("utf-8") if isinstance(cid, bytes) else cid for cid in conv_ids_bytes]

        results = []
        for cid in conv_ids:
            meta = await self.get(cid)
            if meta:
                results.append(meta)

        return results

    async def update_metadata(self, conversation_id: str, updates: dict) -> None:
        """Applies partial updates to conversation metadata and refreshes updated_at."""
        if not self.redis:
            return

        meta_key = self._meta_key(conversation_id)
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        mapping = self._serialize_metadata(updates)
        if mapping:
            await self.redis.hset(meta_key, mapping=mapping)

        # Update the score in the owner's sorted set
        meta = await self.get(conversation_id)
        if meta:
            owner_key = self._owner_key(meta.owner_type, meta.owner_id)
            now_ts = datetime.now(timezone.utc).timestamp()
            await self.redis.zadd(owner_key, {conversation_id: now_ts})

    async def validate_ownership(self, conversation_id: str, owner_type: OwnerType, owner_id: str) -> bool:
        """Checks if the given owner actually owns the conversation."""
        meta = await self.get(conversation_id)
        if not meta:
            return False
        return meta.owner_type == owner_type.value and meta.owner_id == owner_id
