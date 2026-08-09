"""
ExtractionService — Single-Responsibility Content Scraper & Quality Validator.
Invokes HTMLAgent, applies versioned publisher profiles, and evaluates extraction quality.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from agents.ingestion.html_agent import HTMLAgent

logger = logging.getLogger("tech_news.extraction_service")


class ExtractionService:
    def __init__(self):
        self.html_agent = HTMLAgent()

    async def extract_content(
        self, url: str, parser_config: Optional[Dict[str, Any]] = None, source_name: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Extracts clean text content and metadata from an article URL using versioned publisher rules.
        """
        try:
            logger.info(f"ExtractionService: Scraping article URL: {url} (Source: {source_name})")
            result = await self.html_agent.extract_article(url, parser_config=parser_config or {})
            if result and result.get("clean_text") and len(result["clean_text"]) > 150:
                return True, result
            return False, result or {}
        except Exception as e:
            logger.error(f"ExtractionService: HTML extraction failed for {url}: {e}", exc_info=True)
            return False, {"error": str(e)}
