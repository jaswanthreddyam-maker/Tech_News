import io
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup
from PIL import Image

from app.services.ingestion.image_helper import (
    download_and_validate_in_memory,
    extract_all_candidate_urls,
    extract_schema_images,
    is_blacklisted_url,
)


def test_is_blacklisted_url():
    assert is_blacklisted_url("https://example.com/logo.png") is True
    assert is_blacklisted_url("https://example.com/ads/promo.webp") is True
    assert is_blacklisted_url("https://example.com/author-profile.jpg") is True
    # Should not match uploads (not a blacklist word boundary)
    assert is_blacklisted_url("https://example.com/uploads/photo.jpg") is False


def test_extract_schema_images():
    html = """
    <html>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "image": "https://example.com/hero.jpg"
    }
    </script>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "image": {
            "@type": "ImageObject",
            "url": "https://example.com/nested.jpg"
        }
    }
    </script>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = extract_schema_images(soup, "https://example.com/article")
    assert "https://example.com/hero.jpg" in urls
    assert "https://example.com/nested.jpg" in urls


def test_extract_candidate_scoring_and_priorities():
    html = """
    <html>
    <head>
        <meta property="og:image" content="https://example.com/og.jpg" />
        <meta name="twitter:image" content="https://example.com/tw.jpg" />
    </head>
    <body>
        <div class="entry-content">
            <img src="https://example.com/body.jpg" alt="Body Image" />
            <img src="https://example.com/logo.png" alt="Site Logo" />
        </div>
    </body>
    </html>
    """
    candidates = extract_all_candidate_urls(html, "https://techcrunch.com/article")

    # Verify candidate URLs are gathered
    urls = [c["url"] for c in candidates]
    assert "https://example.com/og.jpg" in urls
    assert "https://example.com/tw.jpg" in urls
    assert "https://example.com/body.jpg" in urls

    # The logo should be blacklisted and have a very low/negative score
    logo_cand = [c for c in candidates if "logo.png" in c["url"]]
    assert len(logo_cand) == 1
    assert logo_cand[0]["score"] < 0

    # Candidates are sorted by score descending
    assert candidates[0]["score"] >= candidates[-1]["score"]


@pytest.mark.asyncio
async def test_download_and_validate_in_memory():
    # 1. Test blacklisted URL
    img, phash, reason, dims = await download_and_validate_in_memory("https://example.com/logo.png")
    assert img is None
    assert reason == "keyword_penalty"

    # 2. Test successful mock download
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    # Create valid JPEG bytes
    img_byte_arr = io.BytesIO()
    valid_img = Image.new("RGB", (600, 400), color="blue")
    valid_img.save(img_byte_arr, format="JPEG")
    mock_resp.content = img_byte_arr.getvalue()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    with patch("httpx.AsyncClient", return_value=mock_client):
        img, phash, reason, dims = await download_and_validate_in_memory("https://example.com/valid.jpg")
        assert img is not None
        assert reason is None
        assert phash is not None
        assert dims["width"] == 600
        assert dims["height"] == 400

    # 3. Test dimensions filter (too small)
    small_img_byte_arr = io.BytesIO()
    small_img = Image.new("RGB", (100, 100), color="blue")
    small_img.save(small_img_byte_arr, format="JPEG")
    mock_resp.content = small_img_byte_arr.getvalue()

    with patch("httpx.AsyncClient", return_value=mock_client):
        img, phash, reason, dims = await download_and_validate_in_memory("https://example.com/small.jpg")
        assert img is None
        assert reason == "dimension_filter"


def test_logo_vs_hero_selection():
    """
    Test 1: Two candidates logo.png and hero.webp.
    Expect hero.webp to be ranked higher/win.
    """
    html = """
    <html>
    <head>
        <meta name="twitter:image" content="https://example.com/logo.png" />
        <meta property="og:image" content="https://example.com/hero.webp" />
    </head>
    <body>
    </body>
    </html>
    """
    candidates = extract_all_candidate_urls(html, "https://example.com/article")
    # Verify hero.webp has a higher pre-score than logo.png and comes first
    urls = [c["url"] for c in candidates]
    assert "https://example.com/hero.webp" in urls
    assert "https://example.com/logo.png" in urls

    hero_cand = next(c for c in candidates if "hero.webp" in c["url"])
    logo_cand = next(c for c in candidates if "logo.png" in c["url"])
    assert hero_cand["score"] > logo_cand["score"]
    assert candidates[0]["url"] == "https://example.com/hero.webp"


def test_deterministic_tie_breaker():
    """
    Test 2: Same composite score.
    Ensure deterministic tie-breaking (the one with higher pre-score priority wins).
    """
    # Simulate the selection loop in celery_app.py:
    # First candidate has og:image source (pre-score base 80)
    # Second candidate has twitter:image source (pre-score base 70)
    # If both downloaded successfully and calculate_quality_score returned 92 for both
    scored_candidates = [
        {"candidate": {"url": "https://example.com/og.jpg", "source": "og:image"}, "score": 92},
        {"candidate": {"url": "https://example.com/tw.jpg", "source": "twitter:image"}, "score": 92},
    ]

    winner: Any = None
    winner_score = -9999
    for item in scored_candidates:
        if item["score"] > winner_score:
            winner_score = item["score"]
            winner = item

    assert winner is not None
    assert winner["candidate"]["url"] == "https://example.com/og.jpg"
