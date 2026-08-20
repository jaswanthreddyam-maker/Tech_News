import asyncio
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("tech_news.redis")

# Unified global Async Redis Client
redis_client: aioredis.Redis | None = None


import time

_redis_last_failed = 0.0

def mark_redis_failed():
    global _redis_last_failed
    _redis_last_failed = time.time()

def get_redis_client() -> aioredis.Redis | None:
    global redis_client, _redis_last_failed
    if time.time() - _redis_last_failed < 30.0:
        return None
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            retry_on_timeout=False,
        )

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


_in_memory_locks: dict[str, float] = {}

# Redis-based distributed lock manager (prevents concurrent scraping or scheduled job runs)
class RedisDistributedLock:
    def __init__(self, name: str, expire_seconds: int = 60):
        self.name = f"lock:{name}"
        self.expire_seconds = expire_seconds
        self.client = get_redis_client()
        self.locked = False

    async def acquire(self) -> bool:
        if self.client is None:
            # In-memory fallback lock
            now = time.time()
            exp = _in_memory_locks.get(self.name, 0.0)
            if now < exp:
                self.locked = False
                return False
            _in_memory_locks[self.name] = now + self.expire_seconds
            self.locked = True
            return True

        try:
            res = await self.client.set(self.name, "1", ex=self.expire_seconds, nx=True)
            self.locked = bool(res)
            if self.locked:
                logger.debug(f"Distributed lock successfully ACQUIRED: {self.name}")
            else:
                logger.debug(f"Distributed lock currently HELD: {self.name}")
            return self.locked
        except Exception as e:
            logger.debug(f"Redis lock acquire failed, using local lock: {e}")
            self.locked = True
            return True

    async def release(self):
        if self.locked:
            if self.client:
                try:
                    await self.client.delete(self.name)
                except Exception:
                    pass
            _in_memory_locks.pop(self.name, None)
            self.locked = False
            logger.debug(f"Distributed lock RELEASED: {self.name}")

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
