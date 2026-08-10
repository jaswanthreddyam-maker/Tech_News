"""
CacheService — Event-Driven Cache Invalidation Infrastructure.
Decouples editorial domain logic from Redis cache operations.
"""

import logging
from app.core.redis import get_redis_client

logger = logging.getLogger("tech_news.cache_service")


class CacheService:
    @staticmethod
    async def invalidate_homepage_cache(reason: str = "unspecified") -> bool:
        """
        Invalidates homepage projection cache keys in Redis.
        """
        try:
            from app.api.v1.routes.news import _in_memory_homepage_cache
            _in_memory_homepage_cache["cards"] = None
            _in_memory_homepage_cache["expires_at"] = 0.0

            redis = get_redis_client()
            if redis:
                keys = await redis.keys("editorial:*")
                if keys:
                    await redis.delete(*keys)
                logger.info(f"CacheService: Successfully invalidated homepage cache, Reason: {reason}")
                return True
            return False
        except Exception as e:
            logger.error(f"CacheService: Failed to invalidate homepage cache (reason: {reason}): {e}", exc_info=True)
            return False
