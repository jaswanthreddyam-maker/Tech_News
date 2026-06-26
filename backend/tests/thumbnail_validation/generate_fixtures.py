"""
Thumbnail Certification Framework — Fixture Generator.

Fetches real articles from RSS feeds and saves:
  - fixtures/html/<domain>/<slug>.html   (raw HTML snapshot)
  - fixtures/expected/<domain>/<slug>.json (gold-standard expectations)

Usage:
    cd backend
    set PYTHONPATH=.
    venv\\Scripts\\python.exe -m tests.thumbnail_validation.generate_fixtures
"""

import asyncio
import hashlib
import json
import os
import sys
from urllib.parse import urlparse

import feedparser
import httpx

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.services.ingestion.image_helper import extract_all_candidate_urls

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
HTML_DIR = os.path.join(FIXTURES_DIR, "html")
EXPECTED_DIR = os.path.join(FIXTURES_DIR, "expected")

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── Feed Registry ────────────────────────────────────────────────────────
# Each entry: (feed_url, max_articles_to_snapshot)
FEEDS = [
    ("https://techcrunch.com/feed/", 10),
    ("https://www.theverge.com/rss/index.xml", 10),
    ("https://feeds.arstechnica.com/arstechnica/index", 10),
    ("https://www.tomshardware.com/feeds/all", 10),
    ("https://nvidianews.nvidia.com/releases.xml", 5),
]


def _slug_from_url(url: str) -> str:
    """Derive a filesystem-safe slug from an article URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_")
    if not path:
        path = hashlib.md5(url.encode()).hexdigest()[:12]
    # Truncate overly long slugs
    if len(path) > 120:
        path = path[:100] + "_" + hashlib.md5(path.encode()).hexdigest()[:8]
    return path


async def fetch_html(url: str) -> str | None:
    """Lightweight HTML fetch — no pipeline/agent dependencies."""
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
            print(f"  ✗ HTTP {resp.status_code} for {url}")
            return None
    except Exception as e:
        print(f"  ✗ Error fetching {url}: {e}")
        return None


async def snapshot_article(url: str, domain: str, sem: asyncio.Semaphore):
    """Download one article and create the fixture + expected JSON."""
    slug = _slug_from_url(url)
    domain_html_dir = os.path.join(HTML_DIR, domain)
    domain_expected_dir = os.path.join(EXPECTED_DIR, domain)

    os.makedirs(domain_html_dir, exist_ok=True)
    os.makedirs(domain_expected_dir, exist_ok=True)

    html_path = os.path.join(domain_html_dir, f"{slug}.html")
    expected_path = os.path.join(domain_expected_dir, f"{slug}.json")

    if os.path.exists(html_path):
        return  # already snapshotted

    async with sem:
        html = await fetch_html(url)
        if not html:
            return

        # Save HTML snapshot
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        # Run candidate extraction to pre-populate expected values
        candidates = extract_all_candidate_urls(html, url)
        top_source = candidates[0]["source"] if candidates else "fallback"

        expected = {
            "expected_url": url,
            "expected_domain": domain,
            "expected_fallback": len(candidates) == 0,
            "expected_candidate_count_min": max(1, len(candidates)),
            "expected_thumbnail_source": top_source,
            "expected_dimensions": {"min_width": 200, "min_height": 200},
        }

        with open(expected_path, "w", encoding="utf-8") as f:
            json.dump(expected, f, indent=2)

        print(f"  ✓ {domain}/{slug}")


async def generate():
    sem = asyncio.Semaphore(5)
    tasks = []

    for feed_url, max_articles in FEEDS:
        print(f"Parsing feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"  ✗ Failed to parse feed: {e}")
            continue

        for entry in feed.entries[:max_articles]:
            url = getattr(entry, "link", None)
            if not url:
                continue
            domain = urlparse(url).netloc.replace("www.", "")
            tasks.append(snapshot_article(url, domain, sem))

    if not tasks:
        print("No articles found in feeds.")
        return

    print(f"\nSnapshotting {len(tasks)} articles...")
    await asyncio.gather(*tasks)
    print(f"\nDone. Fixtures saved to {HTML_DIR}")


if __name__ == "__main__":
    asyncio.run(generate())
