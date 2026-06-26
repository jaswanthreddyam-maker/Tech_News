import asyncio
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("tech_news.redis")

# Unified global Async Redis Client
redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    return redis_client


async def close_redis_connection():
    global redis_client
    if redis_client:
        await redis_client.aclose()
        logger.info("Redis client connection pool closed.")


async def verify_redis_connection() -> bool:
    logger.info("Initializing Redis cache startup checks...")
    try:
        client = get_redis_client()
        pong = await asyncio.wait_for(client.ping(), timeout=5.0)
        if pong:
            logger.info("Redis connection successfully verified!")
            return True
    except asyncio.TimeoutError:
        logger.error("Redis cache connection timed out after 5.0 seconds.")
    except Exception as e:
        logger.error(f"Redis cache connection failed: {e!s}")
    return False


# Redis-based distributed lock manager (prevents concurrent scraping or scheduled job runs)
class RedisDistributedLock:
    def __init__(self, name: str, expire_seconds: int = 60):
        self.name = f"lock:{name}"
        self.expire_seconds = expire_seconds
        self.client = get_redis_client()
        self.locked = False

    async def acquire(self) -> bool:
        # SET key value NX PX: NX only sets if not exists, PX sets expiry
        # Returns True if key was set, indicating lock acquired
        res = await self.client.set(self.name, "1", ex=self.expire_seconds, nx=True)
        self.locked = bool(res)
        if self.locked:
            logger.debug(f"Distributed lock successfully ACQUIRED: {self.name}")
        else:
            logger.debug(f"Distributed lock currently HELD: {self.name}")
        return self.locked

    async def release(self):
        if self.locked:
            await self.client.delete(self.name)
            self.locked = False
            logger.debug(f"Distributed lock RELEASED: {self.name}")

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
