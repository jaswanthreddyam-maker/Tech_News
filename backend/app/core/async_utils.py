import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger("tech_news.async_utils")


def run_async_task(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Safely executes an asynchronous coroutine within a synchronous context.
    Prevents event loop leaks and provides uniform error logging for Celery tasks.

    Args:
        coro: The instantiated coroutine to execute (e.g. `my_async_func()`)

    Returns:
        The result of the coroutine.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No current event loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Error during async task execution: {e}", exc_info=True)
        raise
