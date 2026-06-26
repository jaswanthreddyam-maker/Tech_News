import hashlib
import re
import zlib
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """
    Standardize and clean URLs to guarantee reliable deduplication checking.
    Removes tracking parameters, lowercases domains, strips default ports, sorts query params, and strips fragments.
    """
    if not url:
        return ""

    url = url.strip()
    parsed = urlparse(url)

    # 1. Lowercase scheme and domain (netloc)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports if explicitly present
    if ":" in netloc:
        parts = netloc.split(":", 1)
        host, port = parts[0], parts[1]
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            netloc = host

    # 2. Clean query parameters (Remove tracking / utm parameters)
    ignored_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_cid",
        "utm_reader",
        "ref",
        "rss",
        "click",
        "gclid",
        "fbclid",
        "source",
    }

    queries = parse_qsl(parsed.query)
    cleaned_queries = [(k.lower(), v) for k, v in queries if k.lower() not in ignored_params]

    # Sort query parameters to ensure duplicate-safe URL comparison
    cleaned_queries.sort(key=lambda x: (x[0], x[1]))

    # Reassemble queries
    query = urlencode(cleaned_queries) if cleaned_queries else ""

    # 3. Standardize path (lowercase, strip trailing slash)
    path = parsed.path
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")
    if not path:
        path = "/"

    # 4. Reassemble full URL (strip fragment for canonical indexing)
    normalized = urlunparse(
        (
            scheme,
            netloc,
            path,
            "",  # params
            query,
            "",  # fragment
        )
    )

    return normalized


def get_hash(text: str) -> str:
    """
    Generate an MD5 hex digest hash for lookup indexes.
    """
    normalized_text = re.sub(r"\s+", "", text).lower().strip()
    return hashlib.md5(normalized_text.encode("utf-8")).hexdigest()


def compress_content(text: str) -> bytes:
    """
    Compress raw HTML or text payloads using zlib compression for optimal DB size.
    """
    if not text:
        return b""
    return zlib.compress(text.encode("utf-8"), level=9)


def decompress_content(compressed: bytes) -> str:
    """
    Decompress stored BYTEA content back into raw UTF-8 string format.
    """
    if not compressed:
        return ""
    return zlib.decompress(compressed).decode("utf-8")


async def resolve_redirects(url: str) -> str:
    """
    Resolve URL redirects using a highly resilient hierarchy:
    1. HTTP HEAD with follow_redirects=True
    2. HTTP GET with stream=True (closing immediately to avoid body download)
    3. Fallback to original input URL on any error
    """
    import httpx

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(3.0, connect=1.5),
            headers={"User-Agent": "TechNewsTodayBot/1.0 (+http://localhost/bot)"},
        ) as client:
            try:
                # 1. Try HEAD first
                resp = await client.head(url)
                if resp.status_code < 400:
                    return str(resp.url)
            except Exception:
                pass

            # 2. Fallback to streaming GET (read headers only, don't download body)
            try:
                async with client.stream("GET", url) as resp:
                    return str(resp.url)
            except Exception:
                pass
    except Exception:
        pass

    return url
