import asyncio
import logging

import httpx

from app.core.logging import correlation_id_ctx

logger = logging.getLogger("tech_news.http_client")


class AsyncHTTPClient:
    """
    Centralized connection-pooled HTTPX Async Client with exponential retries and log tracing.
    """

    client: httpx.AsyncClient | None = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls.client is None:
            # Set up HTTPX AsyncClient with optimized limits and timeouts
            cls.client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
                follow_redirects=True,
            )
            logger.info("Connection-pooled Async HTTPX Client initialized.")
        return cls.client

    @classmethod
    async def close_client(cls):
        if cls.client:
            await cls.client.aclose()
            cls.client = None
            logger.info("Async HTTPX Client connection pool closed.")

    @classmethod
    async def request(
        cls, method: str, url: str, max_retries: int = 3, backoff_factor: float = 1.5, **kwargs
    ) -> httpx.Response:
        client = cls.get_client()
        correlation_id = correlation_id_ctx.get() or "system"

        # Inject correlation ID header to outgoing request
        headers = kwargs.pop("headers", {})
        headers["X-Correlation-ID"] = correlation_id

        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"HTTP {method} to {url} - Attempt {attempt}/{max_retries}")
                response = await client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP response error {e.response.status_code} on {method} to {url}. "
                    f"Attempt {attempt}/{max_retries}."
                )
                if attempt == max_retries:
                    raise
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"HTTP request failed on {method} to {url}. Attempt {attempt}/{max_retries}. Error: {e!s}"
                )
                if attempt == max_retries:
                    raise

            await asyncio.sleep(delay)
            delay *= backoff_factor

        raise httpx.RequestError("Maximum request retries reached without success.")
