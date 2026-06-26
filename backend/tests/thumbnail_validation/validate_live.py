"""
Thumbnail Certification Framework — Live Validation (Mode A).

Fetches ~N live articles from RSS feeds and runs the full thumbnail
extraction pipeline against real internet sources.

Run manually or on a weekly schedule. NOT intended for CI.

Usage:
    cd backend
    set PYTHONPATH=.
    venv\\Scripts\\python.exe -m tests.thumbnail_validation.validate_live
    venv\\Scripts\\python.exe -m tests.thumbnail_validation.validate_live --max-per-feed 50

Exit code:
    0  — All quality gates passed
    1  — One or more quality gates failed
"""

import argparse
import asyncio
import os
import sys
from urllib.parse import urlparse

import feedparser
import httpx

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from tests.thumbnail_validation.core_validation import (
    generate_report,
    validate_article_thumbnail,
)

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
FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.tomshardware.com/feeds/all",
    "https://nvidianews.nvidia.com/releases.xml",
]


async def fetch_html(url: str, sem: asyncio.Semaphore) -> str | None:
    """Lightweight HTML fetch with concurrency throttle."""
    async with sem:
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.text
                return None
        except Exception:
            return None


async def validate_one(url: str, sem: asyncio.Semaphore) -> dict:
    """Fetch HTML for one URL and run the thumbnail pipeline."""
    html = await fetch_html(url, sem)
    if not html:
        domain = urlparse(url).netloc.replace("www.", "")
        return {
            "url": url,
            "domain": domain,
            "raw_html_length": 0,
            "clean_html_length": 0,
            "compression_ratio": 0,
            "candidate_count": 0,
            "winner_source": "fallback",
            "winner_url": None,
            "winner_phash": None,
            "winner_dims": None,
            "is_fallback": True,
            "failure_reason": "html_fetch_failed",
            "rejection_log": [],
            "timings": {},
            "total_time_sec": 0,
        }
    return await validate_article_thumbnail(html, url)


async def run_live(max_per_feed: int = 20):
    sem = asyncio.Semaphore(5)
    tasks = []

    for feed_url in FEEDS:
        print(f"Parsing feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"  ✗ Failed to parse feed: {e}")
            continue

        urls_added = 0
        for entry in feed.entries:
            if urls_added >= max_per_feed:
                break
            url = getattr(entry, "link", None)
            if url:
                tasks.append(validate_one(url, sem))
                urls_added += 1

        print(f"  → Queued {urls_added} articles")

    print(f"\nExecuting live validation against {len(tasks)} URLs...\n")
    results = await asyncio.gather(*tasks)

    # Print per-article status
    for r in results:
        icon = "✓" if not r["is_fallback"] else "✗"
        print(
            f"  {icon} {r['domain']}: "
            f"candidates={r['candidate_count']} "
            f"winner={r['winner_source']} "
            f"time={r['total_time_sec']:.2f}s"
        )

    # Generate reports
    summary = generate_report(list(results), "live")

    if summary.get("status") == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Thumbnail Pipeline — Live Validation")
    parser.add_argument(
        "--max-per-feed",
        type=int,
        default=20,
        help="Max articles to test per feed (default: 20)",
    )
    args = parser.parse_args()
    asyncio.run(run_live(max_per_feed=args.max_per_feed))


if __name__ == "__main__":
    main()
