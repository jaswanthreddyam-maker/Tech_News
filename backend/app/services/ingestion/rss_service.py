"""
RSSService — Single-Responsibility RSS Ingestion & Feed Scanner.
Downloads RSS feed XML, extracts items, checks GUIDs, and yields raw items for ingestion.
"""

import logging
from typing import List, Dict, Any
from agents.ingestion.rss_agent import RSSIngestionAgent

logger = logging.getLogger("tech_news.rss_service")


class RSSService:
    def __init__(self):
        self.rss_agent = RSSIngestionAgent()

    async def fetch_feed_items_async(self, feed_url: str) -> List[Dict[str, Any]]:
        """
        Parses an RSS/Atom feed URL asynchronously and extracts clean item metadata.
        """
        try:
            logger.info(f"RSSService: Polling RSS feed: {feed_url}")
            items = await self.rss_agent.crawl_feed(feed_url)
            logger.info(f"RSSService: Extracted {len(items)} items from {feed_url}")
            return items
        except Exception as e:
            logger.error(f"RSSService: Failed to parse feed {feed_url}: {e}", exc_info=True)
            return []
