import time
from enum import Enum

from redis.asyncio import Redis


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        redis_client: Redis,
        provider_name: str,
        failure_threshold: int = 5,
        recovery_timeout_sec: int = 600,
    ):
        self.redis = redis_client
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.base_key = f"ai:circuit_breaker:{provider_name}"

    @property
    def _state_key(self) -> str:
        return f"{self.base_key}:state"

    @property
    def _failures_key(self) -> str:
        return f"{self.base_key}:failures"

    @property
    def _opened_at_key(self) -> str:
        return f"{self.base_key}:opened_at"

    async def get_state(self) -> CircuitState:
        state_val = await self.redis.get(self._state_key)
        if not state_val:
            return CircuitState.CLOSED

        state = CircuitState(state_val)
        if state == CircuitState.OPEN:
            opened_at_val = await self.redis.get(self._opened_at_key)
            if opened_at_val:
                opened_at = float(opened_at_val)
                if time.time() - opened_at > self.recovery_timeout_sec:
                    # Transition to half-open
                    await self._set_state(CircuitState.HALF_OPEN)
                    return CircuitState.HALF_OPEN
        return state

    async def record_success(self) -> None:
        state = await self.get_state()
        if state == CircuitState.HALF_OPEN:
            # We recovered! Close the circuit
            await self._set_state(CircuitState.CLOSED)
            await self.redis.delete(self._failures_key)
            await self.redis.delete(self._opened_at_key)
        elif state == CircuitState.CLOSED:
            # Reset failures
            await self.redis.delete(self._failures_key)

    async def record_failure(self) -> None:
        state = await self.get_state()
        if state == CircuitState.HALF_OPEN:
            # Failed during probe. Re-open circuit
            await self._set_state(CircuitState.OPEN)
            await self.redis.set(self._opened_at_key, time.time())
        elif state == CircuitState.CLOSED:
            failures = await self.redis.incr(self._failures_key)
            await self.redis.expire(self._failures_key, 3600)
            if failures >= self.failure_threshold:
                await self._set_state(CircuitState.OPEN)
                await self.redis.set(self._opened_at_key, time.time())

    async def _set_state(self, state: CircuitState) -> None:
        await self.redis.set(self._state_key, state.value)

    async def can_execute(self) -> bool:
        """Returns True if the circuit is closed or half-open."""
        state = await self.get_state()
        return state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]
