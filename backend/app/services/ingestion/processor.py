import re
import zlib
from typing import Any

from bs4 import BeautifulSoup


def decompress_html(compressed_payload: bytes) -> str:
    """
    Decompress zlib compressed raw HTML payload.
    """
    if not compressed_payload:
        return ""
    try:
        return zlib.decompress(compressed_payload).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def generate_slug(title: str) -> str:
    """
    Generate a clean, url-friendly slug from an article title.
    """
    slug = title.lower()
    # Remove special characters
    slug = re.sub(r"[^\w\s-]", "", slug)
    # Replace whitespace with single hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


def calculate_reading_time(text: str) -> int:
    """
    Calculate reading time in minutes based on word count (200 words per minute average).
    """
    if not text:
        return 1
    words = text.split()
    return max(1, len(words) // 200)


def clean_reddit_wrappers(text: str) -> str:
    """
    Strips common Reddit markdown wrappers and boilerplate.
    """
    if not text:
        return ""
    # Remove Reddit empty character markers
    text = text.replace("&#x200B;", "")
    text = text.replace("&amp;#x200B;", "")
    # Remove excessive asterisks/underscores
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"_+", "", text)
    # Clean leading/trailing spaces on lines
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines)


def clean_and_sanitize_html(raw_html_or_text: str) -> str:
    """
    Takes raw HTML or raw text, strips boilerplates/scripts/styles,
    safeguards against XSS attacks, and structures readable semantic paragraphs.
    Preserves lists, headings, and core formatting while preventing raw tags.
    """
    if not raw_html_or_text:
        return "<p>No content available.</p>"

    # Check if raw input is HTML or just plain text
    is_html = bool(BeautifulSoup(raw_html_or_text, "html.parser").find())

    if not is_html:
        # It's plain text, clean Reddit wrappers and wrap in paragraphs
        text = clean_reddit_wrappers(raw_html_or_text)
        paragraphs = text.split("\n\n")
        clean_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
        return clean_html if clean_html else "<p>No content available.</p>"

    # Input is HTML, parse with BeautifulSoup
    soup = BeautifulSoup(raw_html_or_text, "html.parser")

    # 1. Strip unsafe tags to prevent XSS and security vulnerabilities
    unsafe_tags = [
        "script",
        "style",
        "noscript",
        "iframe",
        "embed",
        "object",
        "form",
        "button",
        "input",
        "select",
        "textarea",
        "canvas",
        "svg",
        "audio",
        "video",
        "frame",
        "frameset",
        "applet",
        "meta",
        "link",
    ]
    for tag in soup.find_all(unsafe_tags):
        tag.decompose()

    # 2. Strip unsafe attributes to prevent XSS (onmouseover, onclick, etc.)
    for tag in soup.find_all(True):
        # Keep only safe attributes
        safe_attrs = {}
        for attr, value in tag.attrs.items():
            if attr in ("href", "title", "alt", "src", "class"):
                # Clean javascript: links in href
                if attr == "href" and value.strip().lower().startswith("javascript:"):
                    continue
                safe_attrs[attr] = value
        tag.attrs = safe_attrs

    # 3. Strip common ad/comment boilerplates inside HTML
    boilerplate_patterns = re.compile(
        r"comment|share|social|advertisement|sidebar|menu|footer|header|nav|widget|banner|ad-|promo|popup|cookie",
        re.IGNORECASE,
    )
    for element in soup.find_all(attrs={"class": boilerplate_patterns}):
        element.decompose()
    for element in soup.find_all(attrs={"id": boilerplate_patterns}):
        element.decompose()

    # 4. Extract safe readable tags and build a clean container
    safe_body_elements = soup.find_all(
        ["p", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "code", "strong", "em", "a"]
    )

    if not safe_body_elements:
        # Fallback to general body container text parsing if no standard tags matched
        body_text = soup.get_text(separator="\n\n", strip=True)
        return clean_and_sanitize_html(body_text)

    # Reconstruct clean html tree
    output_html = []

    # Track tags that need to be standalone block-level elements
    block_tags = ("p", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "a")

    for elem in safe_body_elements:
        # Skip elements that are nested inside other safe tags to prevent duplicates
        if elem.parent and elem.parent.name in safe_body_elements:
            continue

        tag_name = elem.name
        text_content = elem.get_text().strip()
        if not text_content:
            continue
            
        contamination_patterns = [
            "skip to main content",
            "tech reviews",
            "sign up",
            "sign in",
            "subscribe to",
            "cookie policy",
            "privacy policy",
            "terms of service",
            "advertisement",
            "more stories",
            "related articles",
            "share this article",
            "follow us on",
            "download the app",
        ]
        
        lower_text = text_content.lower()
        if any(pat in lower_text for pat in contamination_patterns):
            # Skip this element if it contains boilerplate patterns
            continue


        if tag_name in block_tags:
            # Build clean tag
            if tag_name == "a":
                # Convert standalone links into inline paragraphs or strip
                href = elem.get("href", "")
                output_html.append(
                    f'<p><a href="{href}" target="_blank" rel="noopener noreferrer">{text_content}</a></p>'
                )
            elif tag_name == "p":
                output_html.append(f"<p>{text_content}</p>")
            elif tag_name == "pre" or tag_name == "code":
                output_html.append(f"<pre><code>{text_content}</code></pre>")
            elif tag_name.startswith("h"):
                output_html.append(f"<{tag_name} class='font-bold text-white mt-4 mb-2'>{text_content}</{tag_name}>")
            elif tag_name == "blockquote":
                output_html.append(
                    f"<blockquote class='border-l-4 border-accent pl-4 italic my-4 text-neutral-400'>{text_content}</blockquote>"
                )
            else:
                # Lists ul/ol - render child items cleanly
                list_items = "".join(
                    f"<li class='list-disc list-inside ml-4'>{li.get_text().strip()}</li>"
                    for li in elem.find_all("li")
                    if li.get_text().strip()
                )
                if list_items:
                    output_html.append(f"<{tag_name} class='space-y-1 my-3'>{list_items}</{tag_name}>")
        else:
            # Standalone inline tag - wrap in paragraph
            output_html.append(f"<p>{text_content}</p>")

    return "\n".join(output_html)


def map_category_id(title: str, content: str) -> int:
    """
    Dynamically maps articles to seeded PostgreSQL Category IDs based on keyword density.
    Seeded IDs:
    1: Artificial Intelligence
    2: Robotics
    3: Startups
    4: Cybersecurity
    5: Software Development
    6: Space & Science
    """
    text = (title + " " + content).lower()

    # Keyword categories
    keywords = {
        1: [
            "ai",
            "llm",
            "gpt",
            "artificial intelligence",
            "neural",
            "openai",
            "anthropic",
            "deepmind",
            "machine learning",
            "transformer",
            "claude",
        ],
        2: ["robot", "humanoid", "automation", "drone", "cybernetics", "mechanical", "factory floor"],
        3: [
            "funding",
            "round",
            "series a",
            "series b",
            "startup",
            "valuation",
            "acquired",
            "acquisition",
            "venture capital",
            "seed stage",
        ],
        4: [
            "security",
            "cybersecurity",
            "hacked",
            "breach",
            "exploit",
            "vulnerability",
            "zk-snark",
            "encryption",
            "ransomware",
            "malware",
            "auth",
        ],
        5: [
            "next.js",
            "react",
            "rust",
            "framework",
            "python",
            "api",
            "developer",
            "deployment",
            "github",
            "npm",
            "vercel",
            "tailwind",
        ],
        6: ["space", "rocket", "mars", "fusion", "quantum", "nasa", "spacex", "astronomy", "scientific", "reactor"],
    }

    scores = {cat_id: 0 for cat_id in keywords}

    for cat_id, word_list in keywords.items():
        for word in word_list:
            # Count occurrences
            scores[cat_id] += text.count(word)

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] == 0:
        # Default fallback
        return 1
    return best_cat


def generate_seo_metadata(title: str, content: str) -> dict[str, Any]:
    """
    Generate compelling SEO keywords, custom titles, and readability score index.
    """
    seo_title = title if len(title) <= 60 else title[:57] + "..."

    # Extract keywords
    word_freq = {}
    clean_words = re.findall(r"\b\w{4,}\b", content.lower())

    stop_words = {
        "with",
        "that",
        "this",
        "from",
        "they",
        "their",
        "will",
        "would",
        "about",
        "there",
        "them",
        "these",
        "some",
        "more",
        "than",
        "been",
        "have",
        "has",
        "had",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
    }

    for word in clean_words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1

    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords_list = [kw[0] for kw in sorted_keywords[:6]]

    # Calculate readability index (words per sentence + link density approximations)
    sentences = re.split(r"[.!?]+", content)
    words = content.split()

    avg_sentence_len = len(words) / len(sentences) if len(sentences) > 0 else 15
    readability_score = max(30, min(100, int(100 - (avg_sentence_len * 1.5))))

    return {
        "seo_title": seo_title + " - Tech News Today",
        "seo_keywords": ", ".join(keywords_list),
        "readability_score": readability_score,
    }


def extract_controlled_tags(title: str, content: str) -> str:
    """
    Extract tags using a strict, deterministic controlled vocabulary to prevent
    redundant variations and maintain taxonomy consistency.
    Controlled vocabulary:
    - 'artificial-intelligence' (matches ai, llm, gpt, deep learning, machine learning, etc.)
    - 'robotics' (matches robot, humanoid, automation, drone, etc.)
    - 'cybersecurity' (matches security, hack, breach, vulnerability, exploit, malware)
    - 'startups' (matches funding, startup, seed round, series a, venture capital)
    - 'software-development' (matches coding, python, rust, api, framework, react, nextjs, vercel, git)
    - 'space-science' (matches space, rocket, mars, quantum, fusion, nasa, spacex)
    """
    import re

    text_lower = (title + " " + content).lower()

    # Controlled taxonomy maps
    taxonomy = {
        "artificial-intelligence": [
            r"\bai\b",
            r"\bllm\b",
            r"\bgpt\b",
            r"artificial\s+intelligence",
            r"machine\s+learning",
            r"deep\s+learning",
            r"neural\s+network",
            r"openai",
            r"anthropic",
            r"claude",
            r"transformer",
        ],
        "robotics": [r"robot", r"humanoid", r"automation", r"drone", r"cybernetics"],
        "cybersecurity": [
            r"security",
            r"cybersecurity",
            r"breach",
            r"exploit",
            r"vulnerability",
            r"hacked",
            r"malware",
            r"ransomware",
            r"zero-day",
        ],
        "startups": [
            r"funding",
            r"startup",
            r"series\s+[a-z0-9]",
            r"seed\s+round",
            r"valuation",
            r"acquired",
            r"acquisition",
            r"venture\s+capital",
        ],
        "software-development": [
            r"react",
            r"next\.js",
            r"nextjs",
            r"rust\b",
            r"python\b",
            r"api\b",
            r"developer",
            r"github",
            r"vercel",
            r"framework",
            r"tailwind",
        ],
        "space-science": [r"space\b", r"rocket", r"mars\b", r"fusion\b", r"quantum\b", r"nasa\b", r"spacex\b"],
    }

    matched_tags = []
    for tag, patterns in taxonomy.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matched_tags.append(tag)
                break  # Only match once per tag

    if not matched_tags:
        matched_tags = ["tech-innovation"]

    return ", ".join(matched_tags)
