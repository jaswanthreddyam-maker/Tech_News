import logging
from typing import Any

from app.core.capability.ingestion import (
    ArticlePublicationCapability,
    ContentExtractionCapability,
    DeduplicationCapability,
    RSSIngestionCapability,
    SourceValidationCapability,
    WebFetchCapability,
)

logger = logging.getLogger(__name__)

class IngestionWorkflow:
    """
    Deterministic Ingestion Pipeline (Phase 10 Sprint 1).
    Orchestrates the sequence of capabilities.
    """
    def __init__(self):
        self.rss_capability = RSSIngestionCapability()
        self.fetch_capability = WebFetchCapability()
        self.extract_capability = ContentExtractionCapability()
        self.validate_capability = SourceValidationCapability()
        self.dedup_capability = DeduplicationCapability()
        self.publish_capability = ArticlePublicationCapability()

    async def execute(self, feed_url: str, context: Any = None) -> list[dict[str, Any]]:
        logger.info(f"Starting ingestion workflow for feed: {feed_url}")

        # 1. Discover Entries
        rss_result = await self.rss_capability.execute({"feed_url": feed_url}, context)
        entries = rss_result.get("entries", [])

        published_artifacts = []

        for entry in entries:
            entry_url = entry["entry_url"]
            try:
                # 2. Fetch
                fetch_result = await self.fetch_capability.execute({"url": entry_url}, context)

                # 3. Extract
                extract_result = await self.extract_capability.execute({"raw_document": fetch_result}, context)

                # 4. Validate
                val_payload = {
                    "url": extract_result["url"], 
                    "status_code": fetch_result["status_code"]
                }
                val_result = await self.validate_capability.execute(val_payload, context)

                if not val_result["is_approved"]:
                    logger.warning(f"Validation failed for {entry_url}. Skipping.")
                    continue

                # 5. Deduplicate
                dedup_result = await self.dedup_capability.execute({"article": extract_result}, context)
                if dedup_result["is_duplicate"]:
                    logger.info(f"Duplicate detected for {entry_url}. Skipping.")
                    continue

                # 6. Publish
                publish_result = await self.publish_capability.execute({"article": extract_result}, context)

                # Save the complete canonical article object along with artifact ID for Projection
                published_artifacts.append({
                    "artifact_id": publish_result["artifact_id"],
                    "article": extract_result
                })

                logger.info(f"Successfully published {entry_url}")
            except Exception as e:
                logger.error(f"Error processing {entry_url}: {e!s}")

        return published_artifacts
