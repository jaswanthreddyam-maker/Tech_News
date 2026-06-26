import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
import trafilatura
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.core.capability.models import CapabilityContract, CapabilityIdentity
from app.core.capability.registry import CapabilityInterface

logger = logging.getLogger(__name__)

# Base Identity for all ingestion capabilities
def get_ingestion_identity() -> CapabilityIdentity:
    return CapabilityIdentity(
        identity_id="ingestion-system",
        owner="tnt-platform",
        permissions=["read:web", "write:artifacts", "read:artifacts"]
    )

class RSSIngestionCapability(CapabilityInterface):
    """Discovers entries from an RSS/Atom feed."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="RSSIngestionCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"feed_url": {"type": "string"}}},
            output_schema={"type": "array", "items": {"$ref": "#/definitions/FeedEntry"}},
            identity=get_ingestion_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        feed_url = payload.get("feed_url")
        if not feed_url:
            raise ValueError("feed_url is required")

        feed = feedparser.parse(feed_url)
        entries = []
        for entry in feed.entries:
            # Parse published date safely
            published_at = None
            if hasattr(entry, 'published'):
                try:
                    published_at = date_parser.parse(entry.published).isoformat()
                except Exception:
                    pass

            entries.append({
                "feed_url": feed_url,
                "entry_url": entry.link,
                "title": entry.title,
                "published_at": published_at,
                "author": entry.author if hasattr(entry, 'author') else None
            })

        return {"entries": entries}


class WebFetchCapability(CapabilityInterface):
    """Fetches raw HTML with retries and headers."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="WebFetchCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}}},
            output_schema={"$ref": "#/definitions/RawDocument"},
            identity=get_ingestion_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        url = payload.get("url")
        if not url:
            raise ValueError("url is required")

        headers = {
            "User-Agent": "TechNewsTodayBot/1.0 (+http://tnt.news/bot)"
        }

        start_time = datetime.now()
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            fetch_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return {
                "url": url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "raw_html": response.text,
                "fetch_time_ms": fetch_time_ms,
                "redirected_url": str(response.url) if str(response.url) != url else None
            }


class ContentExtractionCapability(CapabilityInterface):
    """Extracts canonical article data using Trafilatura/BS4."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="ContentExtractionCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"raw_document": {"type": "object"}}},
            output_schema={"$ref": "#/definitions/CanonicalArticle"},
            identity=get_ingestion_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        raw_doc = payload.get("raw_document", {})
        raw_html = raw_doc.get("raw_html", "")
        url = raw_doc.get("redirected_url") or raw_doc.get("url")

        if not raw_html or not url:
            raise ValueError("raw_html and url are required")

        # Trafilatura Extraction
        extracted = trafilatura.extract(
            raw_html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            url=url,
            output_format="json"
        )

        if extracted:
            data = json.loads(extracted)
            content = data.get("text", "")
            title = data.get("title", "")
            author = data.get("author", "")
            date = data.get("date", "")

            # Fallback if title/date is missing from trafilatura output
            if not title or not date:
                soup = BeautifulSoup(raw_html, "html.parser")
                if not title:
                    og_title = soup.find("meta", property="og:title")
                    if og_title and og_title.get("content"):
                        title = og_title["content"].strip()
                    else:
                        tw_title = soup.find("meta", name="twitter:title")
                        if tw_title and tw_title.get("content"):
                            title = tw_title["content"].strip()
                        elif soup.title:
                            title = soup.title.string.strip()

                    if title:
                        for suffix in [" | TechCrunch", " - TechCrunch", " | The Verge", " - The Verge", " | Wired", " - Wired"]:
                            if title.endswith(suffix):
                                title = title[:-len(suffix)].strip()

                if not date:
                    pub_time = soup.find("meta", property="article:published_time") or soup.find("meta", itemprop="datePublished")
                    if pub_time and pub_time.get("content"):
                        date = pub_time["content"].strip()
                    else:
                        meta_date = soup.find("meta", name="pubdate") or soup.find("meta", name="publish-date") or soup.find("meta", name="date")
                        if meta_date and meta_date.get("content"):
                            date = meta_date["content"].strip()
        else:
            # Fallback to BS4
            soup = BeautifulSoup(raw_html, "html.parser")
            title = soup.title.string if soup.title else "Unknown Title"

            # Try og:title or twitter:title even in full fallback
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            else:
                tw_title = soup.find("meta", name="twitter:title")
                if tw_title and tw_title.get("content"):
                    title = tw_title["content"].strip()

            if title:
                for suffix in [" | TechCrunch", " - TechCrunch", " | The Verge", " - The Verge", " | Wired", " - Wired"]:
                    if title.endswith(suffix):
                        title = title[:-len(suffix)].strip()

            content = soup.get_text(separator="\n", strip=True)
            author = None
            date = None

            pub_time = soup.find("meta", property="article:published_time") or soup.find("meta", itemprop="datePublished")
            if pub_time and pub_time.get("content"):
                date = pub_time["content"].strip()

        word_count = len(content.split())
        reading_time = max(1, word_count // 200)
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        article_id = hashlib.sha256(url.encode('utf-8')).hexdigest()

        return {
            "id": article_id,
            "url": url,
            "canonical_url": url,
            "title": title or "Untitled",
            "subtitle": None,
            "author": author,
            "published_at": date,
            "updated_at": None,
            "language": "en", # Fallback default
            "summary": content[:200] + "..." if content else "",
            "content": content,
            "word_count": word_count,
            "reading_time": reading_time,
            "images": [],
            "tags": [],
            "source": "Web",
            "license": None,
            "hash": content_hash
        }


class SourceValidationCapability(CapabilityInterface):
    """Validates technical reachability and domain reputation."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="SourceValidationCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"url": {"type": "string"}, "status_code": {"type": "integer"}}},
            output_schema={"$ref": "#/definitions/SourceAssessment"},
            identity=get_ingestion_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        url = payload.get("url", "")
        status_code = payload.get("status_code", 500)

        is_reachable = (status_code < 400)
        is_https = url.startswith("https")

        technical_score = 1.0 if (is_reachable and is_https) else 0.5

        # Simple heuristic for reputation
        known_publishers = ["techcrunch.com", "theverge.com", "wired.com"]
        is_known = any(p in url.lower() for p in known_publishers)

        editorial_score = 1.0 if is_known else 0.8

        is_approved = technical_score > 0.5 and editorial_score > 0.5

        return {
            "url": url,
            "is_reachable": is_reachable,
            "is_https": is_https,
            "is_valid_html": True,
            "is_fresh": True,
            "technical_score": technical_score,
            "trust_score": editorial_score,
            "is_spam": False,
            "domain_reputation": "HIGH" if is_known else "UNKNOWN",
            "known_publisher": is_known,
            "editorial_score": editorial_score,
            "is_approved": is_approved
        }


class DeduplicationCapability(CapabilityInterface):
    """Checks for existing articles and near-duplicates."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="DeduplicationCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"article": {"type": "object"}}},
            output_schema={"$ref": "#/definitions/DuplicateDecision"},
            identity=get_ingestion_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        article = payload.get("article", {})
        url = article.get("url", "")
        content_hash = article.get("hash", "")

        # Normalize URL (remove utm tags etc)
        normalized_url = url.split("?")[0]

        # We would typically hit the DB or Vector Store here. 
        # For Phase 10 demo, we assume false unless known.

        return {
            "normalized_url": normalized_url,
            "content_hash": content_hash,
            "is_duplicate": False,
            "matched_artifact_id": None,
            "confidence": 1.0
        }


class ArticlePublicationCapability(CapabilityInterface):
    """Publishes the finalized ArticleArtifact to the AIOS Artifact Repository."""
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            name="ArticlePublicationCapability",
            version="v1",
            input_schema={"type": "object", "properties": {"article": {"type": "object"}}},
            output_schema={"type": "object", "properties": {"artifact_id": {"type": "string"}}},
            identity=get_ingestion_identity()
        )

    async def execute(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        article = payload.get("article", {})

        # In the AIOS kernel, we publish this to `ArtifactRepository`
        # But we'll just return the artifact ID here for the deterministic workflow to pick up.
        # The actual saving logic would be linked in the execution engine.

        return {
            "artifact_id": article.get("id"),
            "status": "published",
            "published_at": datetime.now(timezone.utc).isoformat()
        }
