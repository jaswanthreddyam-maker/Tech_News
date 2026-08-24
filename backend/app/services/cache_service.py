import logging
from typing import Any

from app.core.redis import get_redis_client

logger = logging.getLogger("tech_news.cache_service")

# Process-level in-memory cache shared with route handlers
in_memory_homepage_cache: dict[str, Any] = {
    "cards": None,
    "expires_at": 0.0,
}


class CacheService:
    @staticmethod
    async def invalidate_homepage_cache(reason: str = "unspecified") -> bool:
        """
        Invalidates homepage projection cache keys in Redis and local memory.
        """
        try:
            in_memory_homepage_cache["cards"] = None
            in_memory_homepage_cache["expires_at"] = 0.0

            redis = get_redis_client()
            if redis:
                keys = await redis.keys("editorial:*")
                if keys:
                    await redis.delete(*keys)
                logger.info(f"CacheService: Successfully invalidated homepage cache, Reason: {reason}")
                return True
            return False
        except Exception as e:
            from app.core.redis import mark_redis_failed
            mark_redis_failed()
            logger.debug(f"CacheService: Redis offline or cache invalidation failed: {e}")
            return False
