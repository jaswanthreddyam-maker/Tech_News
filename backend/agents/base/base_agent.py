import asyncio
import logging

import httpx


class BaseAgent:
    """
    Unified base agent class equipping crawlers with logging, network clients,
    and structured error-handling retry capabilities.
    """
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"tech_news.agents.{name}")
        try:
            from app.core.config import settings
            user_agent = getattr(settings, "USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        except Exception:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    async def execute_request(self, url: str, method: str = "GET", max_retries: int = 3, **kwargs) -> httpx.Response | None:
        """
        Execute async network request with linear backoff retries.
        """
        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"Agent {self.name}: Executing HTTP {method} to {url} (Attempt {attempt}/{max_retries})")
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                self.logger.warning(
                    f"Agent {self.name}: HTTP request failed on attempt {attempt}/{max_retries}. "
                    f"Error: {e!s}"
                )
                # Fail fast on client errors that will never succeed on immediate retry
                if isinstance(e, httpx.HTTPStatusError) and e.response is not None and e.response.status_code in (401, 403, 404):
                    raise e

                if attempt == max_retries:
                    self.logger.error(f"Agent {self.name}: Maximum HTTP retries reached for {url}")
                    if isinstance(e, httpx.HTTPStatusError):
                        raise e
                    return None
                await asyncio.sleep(delay)
                delay *= 2
        return None

    async def shutdown(self):
        """
        Cleanly dispose of pooled HTTP client connection resources.
        """
        await self.client.aclose()
        self.logger.info(f"Agent {self.name}: HTTP client connection pool successfully closed.")
