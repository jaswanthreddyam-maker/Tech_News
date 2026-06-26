import time
from datetime import datetime, timezone
from decimal import Decimal

from redis.asyncio import Redis


class AIBudgetEnforcer:
    def __init__(self, redis_client: Redis, daily_limit: Decimal | float):
        self.redis = redis_client
        self.daily_limit = Decimal(str(daily_limit))

    def _get_daily_key(self) -> str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"ai:budget:daily:{date_str}"

    async def get_current_spend(self) -> Decimal:
        val = await self.redis.get(self._get_daily_key())
        return Decimal(str(val)) if val else Decimal("0.0")

    async def increment_spend(self, amount: Decimal | float) -> None:
        if amount <= 0:
            return
        key = self._get_daily_key()
        await self.redis.incrbyfloat(key, float(amount))
        # ensure key expires in 48 hours to prevent memory leak
        ttl = await self.redis.ttl(key)
        if ttl == -1:
            await self.redis.expire(key, 172800)

    async def check_budget(self) -> bool:
        """Returns True if within budget, False if budget exceeded."""
        if self.daily_limit <= 0:
            return True  # 0 means unlimited
        spend = await self.get_current_spend()
        return spend < self.daily_limit


class AIRateLimiter:
    """A Token Bucket rate limiter for AI requests."""

    def __init__(self, redis_client: Redis, max_requests_per_second: int = 5):
        self.redis = redis_client
        self.max_rps = max_requests_per_second
        self.key = "ai:rate_limit:bucket"

    async def acquire(self) -> bool:
        """
        Attempts to acquire a token from the bucket.
        Returns True if successful, False if rate limited.
        """
        now = time.time()

        # Simple token bucket using Redis Lua script
        script = """
        local key = KEYS[1]
        local max_tokens = tonumber(ARGV[1])
        local now = tonumber(ARGV[2])
        local rate = tonumber(ARGV[1]) -- 1 second refill

        local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
        local tokens = tonumber(bucket[1]) or max_tokens
        local last_update = tonumber(bucket[2]) or now

        -- Refill
        local elapsed = now - last_update
        tokens = tokens + (elapsed * rate)
        if tokens > max_tokens then
            tokens = max_tokens
        end

        -- Try acquire
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
            redis.call('EXPIRE', key, 10)
            return 1
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
            redis.call('EXPIRE', key, 10)
            return 0
        end
        """
        result = await self.redis.eval(script, 1, self.key, self.max_rps, now)
        return bool(result)
