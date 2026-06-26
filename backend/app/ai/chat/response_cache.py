import hashlib
import json
import logging
from datetime import timedelta

from app.core.redis import get_redis_client

logger = logging.getLogger("tech_news.ai.chat.response_cache")


class ResponseCache:
    """
    Caches LLM responses based on semantic query, retrieved context IDs, prompt hash, and model.
    TTL: 24 hours.
    """

    def __init__(self):
        self.redis = get_redis_client()
        self.ttl = timedelta(hours=24)

    def _build_key(self, query: str, retrieved_ids: list[int], prompt_hash: str, model: str, mode: str) -> str:
        # Sort IDs to ensure cache hit regardless of slight ordering differences if deemed identical
        sorted_ids = sorted(retrieved_ids)
        key_content = f"{query}:{sorted_ids}:{prompt_hash}:{model}:{mode}"
        key_hash = hashlib.sha256(key_content.encode("utf-8")).hexdigest()
        return f"ai_cache:{key_hash}"

    async def get(self, query: str, retrieved_ids: list[int], prompt_hash: str, model: str, mode: str) -> dict | None:
        if not self.redis:
            return None

        key = self._build_key(query, retrieved_ids, prompt_hash, model, mode)
        data = await self.redis.get(key)
        if data:
            logger.info(f"AI Cache Hit for mode {mode}")
            return json.loads(data)
        return None

    async def set(
        self, query: str, retrieved_ids: list[int], prompt_hash: str, model: str, mode: str, response_data: dict
    ) -> None:
        if not self.redis:
            return

        key = self._build_key(query, retrieved_ids, prompt_hash, model, mode)
        await self.redis.setex(key, int(self.ttl.total_seconds()), json.dumps(response_data))
