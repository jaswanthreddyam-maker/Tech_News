import xml.etree.ElementTree as ET
from typing import Any

from agents.base.base_agent import BaseAgent


class RSSIngestionAgent(BaseAgent):
    """
    Modular Agent responsible for fetching and parsing XML-based RSS/Atom streams.
    """
    def __init__(self):
        super().__init__("rss_ingestion")

    async def crawl_feed(self, feed_url: str) -> list[dict[str, Any]]:
        """
        Fetch and parse articles from the given RSS or Atom feed URL.
        """
        self.logger.info(f"Crawl Feed: Initializing fetch for RSS feed: {feed_url}")

        response = await self.execute_request(feed_url)
        if not response or not response.text:
            self.logger.error(f"Crawl Feed: Failed to retrieve payload from: {feed_url}")
            return []

        articles = []
        try:
            # Parse XML feed content
            root = ET.fromstring(response.content)

            # 1. Detect standard RSS 2.0 format (items nested under channel)
            channel = root.find("channel")
            if channel is not None:
                self.logger.info("Crawl Feed: Detected standard RSS 2.0 format.")
                for item in channel.findall("item"):
                    article_data = self._parse_rss_item(item)
                    if article_data:
                        articles.append(article_data)

            # 2. Detect Atom format (entries directly nested under feed)
            elif root.tag.endswith("feed"):
                self.logger.info("Crawl Feed: Detected Atom feed format.")
                # Strip XML namespaces for easier node matching
                for child in root:
                    tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if tag_name == "entry":
                        article_data = self._parse_atom_entry(child)
                        if article_data:
                            articles.append(article_data)

            else:
                # Fallback: search for any 'item' or 'entry' tags recursively
                self.logger.warning("Crawl Feed: Unknown XML root tag. Falling back to recursive scan.")
                for node in root.iter():
                    tag_name = node.tag.split("}")[-1] if "}" in node.tag else node.tag
                    if tag_name == "item":
                        article_data = self._parse_rss_item(node)
                        if article_data:
                            articles.append(article_data)
                    elif tag_name == "entry":
                        article_data = self._parse_atom_entry(node)
                        if article_data:
                            articles.append(article_data)

        except ET.ParseError as e:
            self.logger.error(f"Crawl Feed: Failed to parse XML feed schema. Error: {e!s}")
        except Exception as e:
            self.logger.error(f"Crawl Feed: Encountered an unhandled exception while crawling feed. Error: {e!s}")

        self.logger.info(f"Crawl Feed: Successfully parsed {len(articles)} article records from {feed_url}")
        return articles

    def _parse_rss_item(self, item: ET.Element) -> dict[str, Any] | None:
        """
        Parse single RSS 2.0 item node.
        """
        try:
            title = self._find_xml_text(item, "title")
            link = self._find_xml_text(item, "link")
            description = self._find_xml_text(item, "description") or self._find_xml_text(item, "content")
            pub_date = self._find_xml_text(item, "pubDate") or self._find_xml_text(item, "pubdate")

            if not title or not link:
                return None

            return {
                "title": title.strip(),
                "url": link.strip(),
                "summary": description.strip() if description else "",
                "published_at": pub_date.strip() if pub_date else None,
                "raw_html": description or "" # Fallback raw HTML content
            }
        except Exception as e:
            self.logger.warning(f"Failed parsing individual RSS item: {e!s}")
            return None

    def _parse_atom_entry(self, entry: ET.Element) -> dict[str, Any] | None:
        """
        Parse single Atom feed entry node.
        """
        try:
            # Strip namespaces in elements
            title = self._find_xml_text(entry, "title")

            # Atom links are typically attributes <link href="..." />
            link = None
            for child in entry:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "link":
                    link = child.attrib.get("href")
                    if link:
                        break

            summary = self._find_xml_text(entry, "summary") or self._find_xml_text(entry, "content")
            published = self._find_xml_text(entry, "published") or self._find_xml_text(entry, "updated")

            if not title or not link:
                return None

            return {
                "title": title.strip(),
                "url": link.strip(),
                "summary": summary.strip() if summary else "",
                "published_at": published.strip() if published else None,
                "raw_html": summary or ""
            }
        except Exception as e:
            self.logger.warning(f"Failed parsing individual Atom entry: {e!s}")
            return None

    def _find_xml_text(self, parent: ET.Element, tag_name: str) -> str | None:
        """
        Helper method to retrieve the inner text of a tag, ignoring namespaces.
        """
        for child in parent:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag == tag_name:
                return child.text
        return None
