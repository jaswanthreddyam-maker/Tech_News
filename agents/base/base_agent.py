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
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=True,
            headers={
                "User-Agent": "TechNewsTodayBot/1.0 (+http://localhost/bot)"
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
                if attempt == max_retries:
                    self.logger.error(f"Agent {self.name}: Maximum HTTP retries reached for {url}")
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
