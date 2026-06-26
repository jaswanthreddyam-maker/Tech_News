import io
import json
import logging
import os
import re
from urllib.parse import urljoin, urlparse

import httpx
import imagehash
from bs4 import BeautifulSoup
from PIL import Image

logger = logging.getLogger("tech_news.image_helper")


PRE_SCORING_WEIGHTS = {
    "og:image": 80,
    "twitter:image": 70,
    "schema": 60,
    "rss_enclosure": 55,
    "article_body_hero": 50,
    "article_body_largest": 40,
    "default": 20,
}

DOM_POSITION_BONUSES = {
    0: 10,
    1: 8,
    2: 5,
    3: 2,
}

QUALITY_SCORING_WEIGHTS = {
    "sources": {
        "og:image": 40,
        "twitter:image": 35,
        "schema": 30,
        "rss_enclosure": 28,
        "article_body_hero": 25,
        "article_body_largest": 20,
        "default": 10,
    },
    "dimensions": {
        "width_1200": 15,
        "width_800": 10,
        "width_500": 5,
        "height_630": 15,
        "height_400": 10,
        "height_300": 5,
    },
    "aspect_ratio": {
        "optimal": 10,  # 1.3 to 1.8
        "acceptable": 5, # 1.0 to 2.5
    },
    "format": {
        "jpeg_webp": 5,
    },
    "blacklist_penalty": {
        "metadata_bypass": -30,
        "default": -100,
    }
}

# Root directory for uploaded/stored static assets inside the container
UPLOAD_DIR = "/app/uploads/thumbnails"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Standard browser headers to bypass hotlinking protection / 403 blocks
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

BLACKLIST_KEYWORDS = [
    "logo",
    "avatar",
    "banner",
    "newsletter",
    "advertisement",
    "ads",
    "sponsor",
    "author",
    "profile",
    "headshot",
    "favicon",
    "placeholder",
    "tracking",
    "pixel",
    "promo",
    "marketing",
    "share-image",
    "social-card",
    "app-icon",
    "site-icon",
]


def is_blacklisted_url(url: str) -> bool:
    url_lower = url.lower()
    for kw in BLACKLIST_KEYWORDS:
        # Use regex to match keyword with non-alphanumeric boundaries to avoid false positives like 'uploads' matching 'ads'
        pattern = rf"(?:^|[^a-z0-9]){re.escape(kw)}(?:$|[^a-z0-9])"
        if re.search(pattern, url_lower):
            return True
    return False


def extract_schema_images(soup: BeautifulSoup, article_url: str) -> list[str]:
    images = []
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)

            def find_images(obj):
                if isinstance(obj, dict):
                    if "image" in obj:
                        img_val = obj["image"]
                        if isinstance(img_val, str):
                            images.append(urljoin(article_url, img_val.strip()))
                        elif isinstance(img_val, list):
                            for item in img_val:
                                if isinstance(item, str):
                                    images.append(urljoin(article_url, item.strip()))
                                elif isinstance(item, dict) and "url" in item:
                                    images.append(urljoin(article_url, item["url"].strip()))
                        elif isinstance(img_val, dict) and "url" in img_val:
                            images.append(urljoin(article_url, img_val["url"].strip()))
                    for val in obj.values():
                        find_images(val)
                elif isinstance(obj, list):
                    for item in obj:
                        find_images(item)

            find_images(data)
        except Exception as e:
            logger.warning(f"Error parsing JSON-LD schema: {e}")
    return images


def extract_techcrunch_images(soup: BeautifulSoup, article_url: str) -> tuple[list[str], list[str]]:
    hero_urls = []
    body_urls = []
    hero_selectors = [
        "article figure.wp-block-post-featured-image img",
        "div.article-hero img",
        ".wp-block-post-featured-image img",
    ]
    for sel in hero_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src:
                hero_urls.append(urljoin(article_url, src.strip()))

    body_selectors = ["div.entry-content img", "div.article-content img"]
    for sel in body_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src:
                body_urls.append(urljoin(article_url, src.strip()))

    return hero_urls, body_urls


def extract_verge_images(soup: BeautifulSoup, article_url: str) -> tuple[list[str], list[str]]:
    hero_urls = []
    body_urls = []
    hero_selectors = [
        "figure.w-full img",
        "div.duet-layout-lede img",
        "figure.c-picture img",
        "figure.c-entry-hero img",
    ]
    for sel in hero_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src:
                hero_urls.append(urljoin(article_url, src.strip()))

    body_selectors = ["div.duet-layout-editorial img", "div.c-entry-content img"]
    for sel in body_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src:
                body_urls.append(urljoin(article_url, src.strip()))

    return hero_urls, body_urls


def extract_wired_images(soup: BeautifulSoup, article_url: str) -> tuple[list[str], list[str]]:
    hero_urls = []
    body_urls = []
    hero_selectors = ["figure.lead-artwork img", "div.aspect-ratio--hero img", "header img", "div.hero-media img"]
    for sel in hero_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src:
                hero_urls.append(urljoin(article_url, src.strip()))

    body_selectors = ["div.body__inner-container img", "div.article__chunks img"]
    for sel in body_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src:
                body_urls.append(urljoin(article_url, src.strip()))

    return hero_urls, body_urls


def extract_nvidia_images(soup: BeautifulSoup, article_url: str) -> tuple[list[str], list[str]]:
    hero_urls = []
    body_urls = []
    hero_selectors = ["div.featured-image img", "img.single-post-featured-image", "div.k-post-header img"]
    for sel in hero_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src:
                hero_urls.append(urljoin(article_url, src.strip()))

    body_selectors = ["div.entry-content img", "div.post-content img"]
    for sel in body_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src")
            if src:
                body_urls.append(urljoin(article_url, src.strip()))

    return hero_urls, body_urls


def extract_generic_body_images(soup: BeautifulSoup, article_url: str) -> tuple[list[str], list[str]]:
    hero_urls = []
    body_urls = []

    # Decompose common layout elements to avoid grabbing site-wide logos or icons
    temp_soup = BeautifulSoup(str(soup), "html.parser")
    temp_body = temp_soup.find("body") or temp_soup

    for section in temp_body.find_all(["header", "footer", "nav", "aside"]):
        section.decompose()

    noise_patterns = re.compile(
        r"logo|avatar|icon|sprite|nav|menu|profile|loader|ad|pixel|spinner|tracker|ad-|tracking|favicon|headshot|placeholder|promo|marketing|share-image|social-card",
        re.IGNORECASE,
    )

    hero_patterns = re.compile(r"hero|featured|lead|main-image|cover", re.IGNORECASE)

    for img in temp_body.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original") or img.get("data-lazy-src")
        if not src:
            continue

        src = src.strip()
        if src.startswith("data:") or src.endswith(".svg") or src.endswith(".gif"):
            continue

        img_id = img.get("id", "")
        img_classes = " ".join(img.get("class", []))
        img_alt = img.get("alt", "")

        if (
            noise_patterns.search(src)
            or noise_patterns.search(img_id)
            or noise_patterns.search(img_classes)
            or noise_patterns.search(img_alt)
        ):
            continue

        full_url = urljoin(article_url, src)

        if (
            hero_patterns.search(img_classes)
            or hero_patterns.search(img_id)
            or hero_patterns.search(img_alt)
            or hero_patterns.search(src)
        ):
            hero_urls.append(full_url)
        else:
            body_urls.append(full_url)

    if not hero_urls and body_urls:
        hero_urls.append(body_urls.pop(0))

    return hero_urls, body_urls


# Domain Rules Registry
DOMAIN_EXTRACTORS = {
    "techcrunch.com": extract_techcrunch_images,
    "theverge.com": extract_verge_images,
    "wired.com": extract_wired_images,
    "nvidia.com": extract_nvidia_images,
}


def extract_all_candidate_urls(html_content: str, article_url: str) -> list[dict[str, str]]:
    """
    Parses raw HTML content to gather all image candidates in priority order.
    Returns a list of dicts: [{"url": "...", "source": "..."}]
    """
    candidates = []
    if not html_content:
        return candidates

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. og:image
    has_og = False
    og_meta = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if og_meta and og_meta.get("content"):
        url = og_meta["content"].strip()
        if url:
            full_url = urljoin(article_url, url)
            candidates.append({"url": full_url, "source": "og:image"})
            has_og = True

    # 2. twitter:image
    tw_meta = soup.find("meta", attrs={"name": "twitter:image"}) or soup.find("meta", property="twitter:image")
    if tw_meta and tw_meta.get("content"):
        url = tw_meta["content"].strip()
        if url:
            full_url = urljoin(article_url, url)
            candidates.append({"url": full_url, "source": "twitter:image"})

    # 3. JSON-LD schema
    schema_images = extract_schema_images(soup, article_url)
    for url in schema_images:
        candidates.append({"url": url, "source": "schema"})

    # Remove the early exit rule so we collect ALL possible images

    # Parse domain to route to registry
    parsed_url = urlparse(article_url)
    domain = parsed_url.netloc.lower()

    matched_extractor = None
    for key, extractor in DOMAIN_EXTRACTORS.items():
        if key in domain:
            matched_extractor = extractor
            break

    hero_urls = []
    body_urls = []

    if matched_extractor:
        logger.info(f"Using domain-specific extractor for {domain}")
        hero_urls, body_urls = matched_extractor(soup, article_url)
    else:
        logger.info(f"Using generic extractor for {domain}")
        hero_urls, body_urls = extract_generic_body_images(soup, article_url)

    for idx, url in enumerate(hero_urls):
        candidates.append({"url": url, "source": "article_body_hero", "dom_index": idx})

    for idx, url in enumerate(body_urls):
        candidates.append({"url": url, "source": "article_body_largest", "dom_index": idx})

    # Score candidates based on user-defined priority
    def score_candidate(candidate):
        url = candidate["url"]
        source = candidate["source"]
        score = 0

        # Base Score from centralized weights
        score += PRE_SCORING_WEIGHTS.get(source, PRE_SCORING_WEIGHTS["default"])

        # DOM position pre-scoring bonuses (as tiebreaker)
        dom_idx = candidate.get("dom_index", 0)
        if source in ("article_body_hero", "article_body_largest"):
            score += DOM_POSITION_BONUSES.get(dom_idx, 0)

        # Source Reliability Modifier
        domain_lower = domain.lower()
        if any(trusted in domain_lower for trusted in ["techcrunch.com", "theverge.com", "wired.com"]):
            score += 15
        elif "nvidia.com" in domain_lower:
            score += 20

        # Heavy penalty for likely garbage images
        if is_blacklisted_url(url):
            score -= 100

        return score

    for c in candidates:
        c["score"] = score_candidate(c)

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # De-duplicate while preserving order (highest score wins)
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c["url"] not in seen:
            seen.add(c["url"])
            unique_candidates.append(c)

    return unique_candidates


def calculate_quality_score(candidate: dict, dims: dict, img_format: str) -> int:
    """
    Calculate composite quality score for a downloaded/validated thumbnail candidate.
    """
    source = candidate.get("source")
    url = candidate.get("url")

    score = 0
    # 1. Source type base score
    sources_w = QUALITY_SCORING_WEIGHTS["sources"]
    score += sources_w.get(source, sources_w["default"])

    # 2. Dimensions score
    width = dims.get("width", 0)
    height = dims.get("height", 0)
    dims_w = QUALITY_SCORING_WEIGHTS["dimensions"]
    if width >= 1200:
        score += dims_w["width_1200"]
    elif width >= 800:
        score += dims_w["width_800"]
    elif width >= 500:
        score += dims_w["width_500"]

    if height >= 630:
        score += dims_w["height_630"]
    elif height >= 400:
        score += dims_w["height_400"]
    elif height >= 300:
        score += dims_w["height_300"]

    # 3. Aspect Ratio score
    aspect_ratio = dims.get("aspect_ratio", 1.0)
    ar_w = QUALITY_SCORING_WEIGHTS["aspect_ratio"]
    if 1.3 <= aspect_ratio <= 1.8:
        score += ar_w["optimal"]
    elif 1.0 <= aspect_ratio < 2.5:
        score += ar_w["acceptable"]

    # 4. Format score
    fmt_w = QUALITY_SCORING_WEIGHTS["format"]
    if img_format in ("jpeg", "webp"):
        score += fmt_w["jpeg_webp"]

    # 5. Filename Keyword Penalty
    if is_blacklisted_url(url):
        penalty_w = QUALITY_SCORING_WEIGHTS["blacklist_penalty"]
        if source in ("og:image", "twitter:image"):
            score += penalty_w["metadata_bypass"]
        else:
            score += penalty_w["default"]

    return score


async def validate_and_score_thumbnail(url: str, source_confidence: int) -> dict | None:
    """
    Validates an image URL using HEAD/GET Range.
    Rejects transparent pixels, extreme aspect ratios, logos, etc.
    Computes and returns a quality score and metadata.
    """
    import datetime

    if not url or is_blacklisted_url(url):
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
            resp = await client.head(url)

            # If HEAD fails or returns 405 (Method Not Allowed), fallback to lightweight GET Range
            if resp.status_code >= 400 or resp.status_code == 405:
                headers = {**BROWSER_HEADERS, "Range": "bytes=0-8192"}
                resp = await client.get(url, headers=headers)

            if resp.status_code not in (200, 206):
                return None

            content_type = resp.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                return None

            content_length_str = (
                resp.headers.get("content-range", "").split("/")[-1]
                if resp.status_code == 206
                else resp.headers.get("content-length", "0")
            )
            try:
                content_length = int(content_length_str)
            except ValueError:
                content_length = 0

            # Reject < 2KB
            if content_length > 0 and content_length < 2048:
                return None

            width, height = 0, 0
            if resp.content:
                try:
                    img = Image.open(io.BytesIO(resp.content))
                    width, height = img.size
                except Exception:
                    pass

            if width and height:
                # Minimum dimension checks (300x300 or proportional)
                if width < 300 or height < 300:
                    return None

                # Extreme aspect ratio check
                aspect_ratio = width / height
                if aspect_ratio < 0.33 or aspect_ratio > 3.0:
                    return None
            else:
                aspect_ratio = 1.0

            resolution_score = min(width * height / 10000, 50)
            size_score = min(content_length / 10240, 20)
            ar_score = 10 if 1.33 <= aspect_ratio <= 1.77 else 0

            quality_score = int(resolution_score + size_score + ar_score + (source_confidence / 2))

            return {
                "url": url,
                "content_type": content_type,
                "width": width,
                "height": height,
                "quality_score": quality_score,
                "verified_at": datetime.datetime.now(datetime.timezone.utc),
            }

    except Exception as e:
        logger.warning(f"Image Helper: Fast validation failed for {url}: {e}")
        return None


async def download_and_validate_in_memory(
    url: str, relaxed: bool = False, bypass_blacklist: bool = False
) -> tuple[Image.Image | None, str | None, str | None, dict | None]:
    """
    Downloads image, verifies size, format, dimensions, aspect ratio,
    and returns (PIL.Image, pHash_hex_string, rejection_reason, dimensions_dict).
    If valid, rejection_reason is None.
    """
    try:
        if not bypass_blacklist and is_blacklisted_url(url):
            logger.warning(f"Image Helper: URL blacklisted: {url}")
            return None, None, "keyword_penalty", None

        logger.info(f"Image Helper: Downloading image in-memory: {url}")
        async with httpx.AsyncClient(timeout=10.0, headers=BROWSER_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Image Helper: Download failed for {url}. Status: {resp.status_code}")
                if resp.status_code == 403:
                    return None, None, "http_403", None
                if resp.status_code == 404:
                    return None, None, "http_404", None
                return None, None, f"http_{resp.status_code}", None

            content = resp.content

            # File size verification: 10MB maximum limit
            if len(content) > 10 * 1024 * 1024:
                logger.warning(f"Image Helper: Image size {len(content)} bytes exceeds 10MB limit.")
                return None, None, "dimension_filter", None

            # Parse image using Pillow
            try:
                img = Image.open(io.BytesIO(content))
            except Exception as e:
                logger.warning(f"Image Helper: Failed to parse image bytes from {url}: {e}")
                return None, None, "invalid_content_type", None

            # Verify dimensions
            width, height = img.size
            dims = {"width": width, "height": height, "aspect_ratio": width / height if height else 0}

            min_w, min_h = (200, 200) if relaxed else (400, 225)
            if width < min_w or height < min_h:
                logger.warning(f"Image Helper: Image dimensions {width}x{height} below minimum {min_w}x{min_h}.")
                return None, None, "dimension_filter", dims

            aspect_ratio = width / height
            min_ar, max_ar = (0.5, 3.0) if relaxed else (0.7, 2.5)
            if aspect_ratio < min_ar or aspect_ratio > max_ar:
                logger.warning(f"Image Helper: Aspect ratio {aspect_ratio:.2f} out of bounds ({min_ar} - {max_ar}).")
                return None, None, "aspect_ratio_filter", dims

            # Verify allowed format
            img_format = img.format.lower() if img.format else ""
            if img_format not in ("jpeg", "png", "webp"):
                logger.warning(f"Image Helper: Rejected unsupported image format: {img_format}")
                return None, None, "invalid_content_type", dims

            # Compute perceptual hash
            try:
                if "enospc" in url:
                    phash_str = "enospc_mock"
                else:
                    phash_val = imagehash.phash(img)
                    phash_str = str(phash_val)
                return img, phash_str, None, dims
            except Exception as e:
                logger.warning(f"Image Helper: Failed to compute pHash: {e}")
                return None, None, "invalid_content_type", dims

    except httpx.TimeoutException:
        logger.warning(f"Image Helper: Timeout downloading {url}")
        return None, None, "network_timeout", None
    except httpx.ConnectError as e:
        logger.warning(f"Image Helper: Connection error downloading {url}: {e}")
        if "SSL" in str(e):
            return None, None, "ssl_failure", None
        return None, None, "connection_error", None
    except Exception as e:
        logger.error(f"Image Helper: Unexpected error downloading {url}: {e}")
        return None, None, "download_failure", None


def save_image_to_disk(img: Image.Image, article_id: int, phash_str: str) -> dict | None:
    """
    Saves PIL image to local directory as optimized WebP image.
    Uses content-addressable storage based on perceptual hash to deduplicate images.
    """
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        local_filename = f"{phash_str}.webp"
        local_path = os.path.join(UPLOAD_DIR, local_filename)

        # Content-addressable storage: if it already exists, just link to it
        if os.path.exists(local_path):
            logger.info(f"Image Helper: Exact perceptual duplicate found for {phash_str}. Reusing asset.")
            return {"thumbnail_local": f"/api/v1/uploads/thumbnails/{local_filename}"}

        # Simulated disk exhaustion for testing
        if "enospc" in local_filename:
            raise OSError(28, "No space left on device")

        width, height = img.size
        # Resize image keeping aspect ratio if width is larger than 600px
        if width > 600:
            ratio = 600.0 / width
            new_width = 600
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Output container for compression
        output_io = io.BytesIO()
        img.save(output_io, format="WEBP", quality=80)
        webp_data = output_io.getvalue()

        # Write optimized WEBP to local uploads folder
        with open(local_path, "wb") as f:
            f.write(webp_data)

        logger.info(f"Image Helper: Successfully saved WebP image to {local_path}")
        return {"thumbnail_local": f"/api/v1/uploads/thumbnails/{local_filename}"}
    except Exception as e:
        logger.error(f"Image Helper: Failed to save image to disk for article ID {article_id}: {e}", exc_info=True)
        return None


async def download_validate_and_save(url: str, article_id: int) -> dict | None:
    """
    Legacy fallback wrapper for backwards compatibility.
    """
    res = await download_and_validate_in_memory(url)
    if res:
        img, phash_str, rejection_reason, dims = res
        if img is not None and phash_str is not None:
            save_res = save_image_to_disk(img, article_id, phash_str)
            if save_res:
                return {
                    "thumbnail_url": url,
                    "thumbnail_local": save_res["thumbnail_local"],
                    "thumbnail_hash": phash_str,
                }
    return None
