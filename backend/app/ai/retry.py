import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from app.ai.exceptions import AIProviderError, AIProviderTimeout

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 4.0


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
    retryable_errors: tuple[type[Exception], ...] = (AIProviderError, AIProviderTimeout, TimeoutError),
) -> tuple[T, int]:
    attempts = 0
    last_error: Exception | None = None

    while attempts < max(1, policy.max_attempts):
        try:
            result = await operation()
            return result, attempts
        except retryable_errors as exc:
            last_error = exc
            attempts += 1
            if attempts >= max(1, policy.max_attempts):
                break
            delay = min(policy.base_delay_seconds * (2 ** (attempts - 1)), policy.max_delay_seconds)
            if delay > 0:
                await asyncio.sleep(delay)

    if last_error is not None:
        raise last_error
    raise AIProviderError("AI operation failed before an attempt was recorded.")
