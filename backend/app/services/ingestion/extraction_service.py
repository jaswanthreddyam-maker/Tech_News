"""
ExtractionService — Single-Responsibility Content Scraper & Quality Validator.
Invokes HTMLAgent, applies versioned publisher profiles, and returns structured ExtractionResult.
"""

from dataclasses import dataclass
import logging
from typing import Dict, Any, Optional
from agents.ingestion.html_agent import HTMLAgent
import httpx

logger = logging.getLogger("tech_news.extraction_service")


@dataclass
class ExtractionResult:
    status: str  # "SUCCESS", "HTTP_403", "HTTP_404", "HTTP_429", "HTTP_5XX", "TIMEOUT", "EMPTY_BODY", "PARSER_FAILURE", "NETWORK_ERROR"
    canonical_content: str = ""
    word_count: int = 0
    raw_html: str = ""
    title: str = ""
    content_score: float = 0.0
    density_score: float = 0.0
    error_message: Optional[str] = None


class ExtractionService:
    def __init__(self):
        self.html_agent = HTMLAgent()

    async def extract_content(
        self, url: str, parser_config: Optional[Dict[str, Any]] = None, source_name: str = ""
    ) -> ExtractionResult:
        """
        Extracts clean text content and metadata from an article URL using versioned publisher rules.
        Returns a standardized ExtractionResult.
        """
        try:
            logger.info(f"ExtractionService: Scraping article URL: {url} (Source: {source_name})")
            result = await self.html_agent.extract_article(url, parser_config=parser_config or {}, source_name=source_name)
            
            if not result:
                return ExtractionResult(
                    status="EMPTY_BODY",
                    error_message="HTMLAgent returned empty response or unparseable DOM"
                )

            clean_text = result.get("clean_text") or ""
            word_count = result.get("word_count") or len(clean_text.split())

            if result.get("status_code") == 403 or result.get("error_type") == "HTTP_403":
                return ExtractionResult(status="HTTP_403", error_message="403 Forbidden")
            elif result.get("status_code") == 404 or result.get("error_type") == "HTTP_404":
                return ExtractionResult(status="HTTP_404", error_message="404 Not Found")
            elif result.get("status_code") == 429 or result.get("error_type") == "HTTP_429":
                return ExtractionResult(status="HTTP_429", error_message="429 Too Many Requests")

            if clean_text and word_count > 0:
                return ExtractionResult(
                    status="SUCCESS",
                    canonical_content=clean_text,
                    word_count=word_count,
                    raw_html=result.get("raw_html", ""),
                    title=result.get("title", ""),
                    content_score=result.get("content_score", 50.0),
                    density_score=result.get("density_score", 0.5),
                )
            
            return ExtractionResult(
                status="PARSER_FAILURE",
                error_message="Parser returned zero-length clean text"
            )

        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response else 0
            if code == 403:
                status_code = "HTTP_403"
            elif code == 404:
                status_code = "HTTP_404"
            elif code == 429:
                status_code = "HTTP_429"
            elif code >= 500:
                status_code = "HTTP_5XX"
            else:
                status_code = f"HTTP_{code}"
            logger.warning(f"ExtractionService: HTTP error {code} for {url}")
            return ExtractionResult(status=status_code, error_message=str(e))
        except httpx.TimeoutException as e:
            logger.warning(f"ExtractionService: Timeout fetching {url}")
            return ExtractionResult(status="TIMEOUT", error_message=str(e))
        except Exception as e:
            logger.error(f"ExtractionService: Exception extracting {url}: {e}", exc_info=True)
            return ExtractionResult(status="NETWORK_ERROR", error_message=str(e))
