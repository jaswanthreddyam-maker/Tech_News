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
        Parse single RSS 2.0 item node, extracting title, url, summary, date, and thumbnail image.
        """
        try:
            title = self._find_xml_text(item, "title")
            link = self._find_xml_text(item, "link")
            description = self._find_xml_text(item, "description") or self._find_xml_text(item, "content") or self._find_xml_text(item, "encoded")
            pub_date = self._find_xml_text(item, "pubDate") or self._find_xml_text(item, "pubdate")

            if not title or not link:
                return None

            thumbnail_url = self._extract_image_url(item, description, link.strip())

            return {
                "title": title.strip(),
                "url": link.strip(),
                "summary": description.strip() if description else "",
                "published_at": pub_date.strip() if pub_date else None,
                "thumbnail_url": thumbnail_url,
                "raw_html": description or "" # Fallback raw HTML content
            }
        except Exception as e:
            self.logger.warning(f"Failed parsing individual RSS item: {e!s}")
            return None

    def _parse_atom_entry(self, entry: ET.Element) -> dict[str, Any] | None:
        """
        Parse single Atom feed entry node, extracting title, url, summary, date, and thumbnail image.
        """
        try:
            title = self._find_xml_text(entry, "title")

            # Atom links are typically attributes <link href="..." />
            link = None
            for child in entry:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "link":
                    rel = child.attrib.get("rel", "alternate")
                    if rel in ("alternate", "canonical") or not link:
                        link = child.attrib.get("href")

            summary = self._find_xml_text(entry, "summary") or self._find_xml_text(entry, "content")
            published = self._find_xml_text(entry, "published") or self._find_xml_text(entry, "updated")

            if not title or not link:
                return None

            thumbnail_url = self._extract_image_url(entry, summary, link.strip())

            return {
                "title": title.strip(),
                "url": link.strip(),
                "summary": summary.strip() if summary else "",
                "published_at": published.strip() if published else None,
                "thumbnail_url": thumbnail_url,
                "raw_html": summary or ""
            }
        except Exception as e:
            self.logger.warning(f"Failed parsing individual Atom entry: {e!s}")
            return None

    def _extract_image_url(self, element: ET.Element, html_content: str | None, article_url: str = "") -> str | None:
        """
        Extract image/thumbnail URL from media:content, media:thumbnail, enclosure, embedded <img>, or live og:image.
        """
        import re
        import html

        # 1. Check direct child nodes (media:content, media:thumbnail, enclosure)
        for child in element:
            tag = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
            
            if tag in ("thumbnail", "content") and "url" in child.attrib:
                url = child.attrib["url"]
                medium = child.attrib.get("medium", "")
                if medium == "image" or not medium:
                    if self._is_valid_image_url(url):
                        return html.unescape(url)

            if tag == "enclosure" and "url" in child.attrib:
                enc_type = child.attrib.get("type", "")
                if "image" in enc_type or self._is_valid_image_url(child.attrib["url"]):
                    return html.unescape(child.attrib["url"])

        # 2. Check all text and content nodes inside the element for embedded <img> tags
        for child in element:
            child_text = child.text or ""
            img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', child_text, re.IGNORECASE)
            if img_match:
                candidate = img_match.group(1)
                if self._is_valid_image_url(candidate):
                    return html.unescape(candidate)

        # 3. Check for embedded <img> in provided html_content
        if html_content:
            img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html_content, re.IGNORECASE)
            if img_match:
                candidate = img_match.group(1)
                if self._is_valid_image_url(candidate):
                    return html.unescape(candidate)

        # 4. Live fallback: scrape og:image / twitter:image from article URL head
        if article_url and (article_url.startswith("http://") or article_url.startswith("https://")):
            og_img = self._fetch_og_image(article_url)
            if og_img:
                return og_img

        return None

    def _fetch_og_image(self, url: str) -> str | None:
        """Quickly stream <head> of article web page to extract og:image or twitter:image."""
        import urllib.request
        import re
        import html

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                chunk = resp.read(65536).decode("utf-8", errors="ignore")
                m = re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']', chunk, re.IGNORECASE)
                if not m:
                    m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']', chunk, re.IGNORECASE)
                if m:
                    candidate = html.unescape(m.group(1))
                    if self._is_valid_image_url(candidate):
                        return candidate
        except Exception:
            pass
        return None

    def _is_valid_image_url(self, url: str | None) -> bool:
        if not url or not isinstance(url, str):
            return False
        url_lower = url.lower().strip()
        if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
            return False
        # Filter out tracking pixels, badges, and avatars
        if any(bad in url_lower for bad in ["1x1", "pixel", "tracker", "favicon", "gravatar", "author-avatar", "badge"]):
            return False
        return True

    def _find_xml_text(self, parent: ET.Element, tag_name: str) -> str | None:
        """
        Helper method to retrieve the inner text of a tag, ignoring namespaces.
        """
        for child in parent:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag.lower() == tag_name.lower():
                return child.text
        return None
