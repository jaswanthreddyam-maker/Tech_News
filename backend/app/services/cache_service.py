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
            redis = get_redis_client()
            if redis:
                await redis.delete("editorial:v1:homepage_ranked_ids")
                logger.info(f"CacheService: Successfully invalidated homepage cache ('editorial:v1:homepage_ranked_ids'), Reason: {reason}")
                return True
            return False
        except Exception as e:
            logger.error(f"CacheService: Failed to invalidate homepage cache (reason: {reason}): {e}", exc_info=True)
            return False
