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
    Takes raw HTML or raw text, isolates the primary editorial container,
    strips all non-editorial noise (navigation, footers, sub-menus, widgets, boilerplate),
    prevents duplicate text line extraction, and produces clean semantic HTML.
    """
    if not raw_html_or_text:
        return "<p>No content available.</p>"

    # 1. Check if raw input is HTML or just plain text
    is_html = bool(BeautifulSoup(raw_html_or_text, "html.parser").find())

    if not is_html:
        text = clean_reddit_wrappers(raw_html_or_text)
        paragraphs = text.split("\n\n")
        clean_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
        return clean_html if clean_html else "<p>No content available.</p>"

    soup = BeautifulSoup(raw_html_or_text, "html.parser")

    # 2. Decompose unsafe and non-editorial structural tags
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
        "header",
        "footer",
        "nav",
        "aside",
        "menu",
    ]
    for tag in soup.find_all(unsafe_tags):
        tag.decompose()

    # 3. Decompose non-editorial containers by class / id / role attributes
    noise_patterns = re.compile(
        r"header|footer|nav|sidebar|menu|breadcrumb|site-nav|global-nav|ad-|advertisement|"
        r"promo|popup|cookie|modal|social|share|comment|related|trending|popular|see-all|"
        r"author-bio|follow-|subscribe|newsletter|topic-chip|topic-subscribe|widget|toolbar|"
        r"rating-card|rating-widget|privacy|terms",
        re.IGNORECASE,
    )
    for element in soup.find_all(attrs={"class": noise_patterns}):
        element.decompose()
    for element in soup.find_all(attrs={"id": noise_patterns}):
        element.decompose()
    for element in soup.find_all(
        attrs={"role": re.compile(r"navigation|banner|contentinfo|complementary", re.IGNORECASE)}
    ):
        element.decompose()

    # 4. Clean attributes to prevent XSS while keeping safe attributes
    for tag in soup.find_all(True):
        safe_attrs = {}
        for attr, value in tag.attrs.items():
            if attr in ("href", "title", "alt", "src", "class"):
                if attr == "href" and str(value).strip().lower().startswith("javascript:"):
                    continue
                safe_attrs[attr] = value
        tag.attrs = safe_attrs

    # 5. Locate Primary Editorial Container
    container = None
    container_selectors = [
        "article",
        '[role="main"]',
        "main",
        ".article-body",
        ".post-content",
        ".entry-content",
        ".article-content",
        ".story-body",
        ".content-body",
        ".review-body",
        "#article-body",
        "#main-content",
        ".main-content",
    ]
    for selector in container_selectors:
        found = soup.select_one(selector)
        if found:
            container = found
            break

    if not container:
        container = soup.find("body") or soup

    # 6. Extract block-level content elements inside container
    block_elements = container.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "blockquote", "pre", "table", "figure"]
    )

    if not block_elements:
        body_text = container.get_text(separator="\n\n", strip=True)
        return clean_and_sanitize_html(body_text)

    output_blocks = []
    seen_texts = set()

    contamination_patterns = [
        "skip to main content",
        "see all",
        "posts from this topic",
        "follow topics and authors",
        "cookie policy",
        "privacy policy",
        "terms of service",
        "advertisement",
        "more stories",
        "related articles",
        "share this article",
        "follow us",
        "download the app",
        "sign up",
        "sign in",
        "subscribe to",
        "photography by",
        "all rights reserved",
        "copyright",
    ]

    for elem in block_elements:
        # Prevent parent-child double processing (e.g. if elem is <p> inside a <blockquote> or <figure>)
        if elem.parent and elem.parent.name in ["p", "blockquote", "figure", "li", "td", "th"]:
            continue

        tag_name = elem.name

        # Preserve structured HTML tables
        if tag_name == "table":
            table_text = elem.get_text().strip()
            norm_table = re.sub(r"\s+", " ", table_text.lower())
            if norm_table and norm_table not in seen_texts:
                seen_texts.add(norm_table)
                output_blocks.append(
                    f'<div className="overflow-x-auto my-4"><table className="w-full border-collapse border border-border text-sm">{elem.decode_contents()}</table></div>'
                )
            continue

        # Figure handling: render clean caption
        if tag_name == "figure":
            caption_tag = elem.find("figcaption")
            caption_text = caption_tag.get_text().strip() if caption_tag else ""
            if caption_text:
                norm_cap = re.sub(r"\s+", " ", caption_text.lower())
                if norm_cap not in seen_texts:
                    seen_texts.add(norm_cap)
                    output_blocks.append(f'<p class="text-xs italic text-muted-foreground my-2">{caption_text}</p>')
            continue

        text_content = elem.get_text().strip()
        if not text_content:
            continue

        # Normalize text for deduplication
        norm_text = re.sub(r"\s+", " ", text_content.lower())

        # Deduplication check
        if norm_text in seen_texts:
            continue

        # Contamination check
        if any(pat in norm_text for pat in contamination_patterns):
            continue

        # Reject short navigational fragment lines (e.g. standalone "Amazon", "Apple", "Tech", "Reviews")
        words = text_content.split()
        if len(words) <= 3 and tag_name == "p":
            if not re.search(r"[.!?:]", text_content):
                continue

        # Mark as seen
        seen_texts.add(norm_text)

        # Build clean HTML output tags
        if tag_name == "p":
            output_blocks.append(f"<p>{text_content}</p>")
        elif tag_name.startswith("h"):
            output_blocks.append(
                f"<{tag_name} class='font-bold text-foreground mt-4 mb-2'>{text_content}</{tag_name}>"
            )
        elif tag_name == "blockquote":
            output_blocks.append(
                f"<blockquote class='border-l-4 border-primary pl-4 italic my-4 text-muted-foreground'>{text_content}</blockquote>"
            )
        elif tag_name == "pre":
            output_blocks.append(f"<pre><code>{text_content}</code></pre>")
        elif tag_name in ["ul", "ol"]:
            list_items = []
            for li in elem.find_all("li", recursive=False) or elem.find_all("li"):
                li_text = li.get_text().strip()
                norm_li = re.sub(r"\s+", " ", li_text.lower())
                if li_text and norm_li not in seen_texts:
                    seen_texts.add(norm_li)
                    list_items.append(f"<li class='list-disc list-inside ml-4'>{li_text}</li>")
            if list_items:
                output_blocks.append(f"<{tag_name} class='space-y-1 my-3'>{''.join(list_items)}</{tag_name}>")

    return "\n".join(output_blocks) if output_blocks else "<p>No content available.</p>"


def _normalize_text(text: str) -> str:
    return text.lower() if text else ""

def _count_matches(text: str, keywords: list[str]) -> int:
    if not text:
        return 0
    sorted_kws = sorted(keywords, key=len, reverse=True)
    count = 0
    text_copy = " " + text + " "
    for kw in sorted_kws:
        pattern = r'\b' + re.escape(kw) + r'\b'
        matches = len(re.findall(pattern, text_copy))
        if matches > 0:
            count += matches
            text_copy = re.sub(pattern, ' ', text_copy)
    return count

def map_category_slug(title: str, content: str, source_name: str = "") -> str:
    """
    Multi-signal classifier with Evidence-Density Tie-Breaker and Protected Positives.
    """
    DICTIONARY = {
        "artificial-intelligence": {
            "positive": ["llm", "transformer", "generative ai", "chatgpt", "neural network", "inference", "machine learning", "training", "gemini", "claude", "gpt", "ai model", "ai agents", "prompt engineering"],
            "negative": ["laptop", "tablet", "smartphone", "review", "funding", "lawsuit", "legislation", "smart home", "cybersecurity"],
            "priors": ["OpenAI Blog", "Anthropic News", "Google DeepMind", "NVIDIA AI Blog", "Google Blog"]
        },
        "cybersecurity": {
            "positive": ["vulnerability", "zero-day", "zero day", "breach", "hacked", "malware", "ransomware", "encryption", "patched", "cve", "exploit", "authentication", "cyber", "cybersecurity", "penetration testing"],
            "negative": ["funding", "startup", "revenue"],
            "priors": []
        },
        "hardware": {
            "positive": ["gpu", "cpu", "processor", "semiconductor", "chip", "silicon", "laptop", "tablet", "smartphone", "review", "gadget", "wacom", "battery", "rtx", "iphone", "macbook", "hardware", "architecture"],
            "negative": ["software", "cloud"],
            "priors": ["NVIDIA AI Blog", "The Verge"]
        },
        "robotics": {
            "positive": ["robot", "robotics", "autonomous", "drone", "self-driving", "humanoid", "waymo", "robotaxi", "boston dynamics"],
            "negative": [],
            "priors": ["Google DeepMind"]
        },
        "science": {
            "positive": ["quantum", "physics", "fusion", "reactor", "space", "nasa", "spacex", "astronomy", "biotech", "medical", "genome", "weather forecasting", "cyclone", "climate"],
            "negative": [],
            "priors": []
        },
        "startups-and-business": {
            "positive": ["funding", "series a", "series b", "venture capital", "valuation", "acquired", "acquisition", "seed stage", "revenue", "q1", "q2", "q3", "q4", "ipo", "enterprise", "startup", "raises"],
            "negative": ["review", "gameplay", "zero-day"],
            "priors": ["TechCrunch"]
        },
        "policy": {
            "positive": ["legislation", "executive order", "regulation", "senate", "congress", "white house", "eu", "lawmaker", "lawsuit", "ruling", "copyright", "antitrust", "mandate", "fcc", "ftc"],
            "negative": [],
            "priors": []
        },
        "technology": {
            "positive": ["browser", "app", "update", "feature", "web", "streaming", "streaming service", "roku", "software"],
            "negative": [],
            "priors": ["The Verge", "TechCrunch", "Ars Technica", "Hacker News"]
        }
    }

    SPECIALIZED_CATEGORIES = [c for c in DICTIONARY.keys() if c != "technology"]

    title_norm = _normalize_text(title)
    content_norm = _normalize_text(content)
    
    scores = {}
    details = {}

    for cat in SPECIALIZED_CATEGORIES:
        d = DICTIONARY[cat]
        t_count = _count_matches(title_norm, d["positive"])
        c_count = _count_matches(content_norm, d["positive"])
        n_t_count = _count_matches(title_norm, d["negative"])
        n_c_count = _count_matches(content_norm, d["negative"])
        
        t_score = min(t_count * 3, 9)
        c_score = min(c_count * 1, 5)
        
        # Protected Positives
        raw_neg = (n_t_count + n_c_count) * -5
        if t_score >= 3 and n_t_count == 0:
            raw_neg = 0
            
        n_score = max(raw_neg, -10)
        s_score = 2 if source_name in d["priors"] else 0
        
        total = t_score + c_score + n_score + s_score
        scores[cat] = total
        details[cat] = {"t": t_score, "c": c_score, "n": n_score, "s": s_score}

    # Sort using total score, then title score, then content score (Evidence-Density Tie-Breaker)
    def sort_key(item):
        cat, score = item
        d = details[cat]
        return (score, d["t"], d["c"])

    sorted_cats = sorted(scores.items(), key=sort_key, reverse=True)
    best_cat, best_score = sorted_cats[0]
    second_best_cat, second_best_score = sorted_cats[1] if len(sorted_cats) > 1 else (None, 0)
    
    margin = best_score - second_best_score
    
    # 1. Confidence Gate
    pass_conf = best_score >= 4
    
    # 2. Direct Evidence Gate
    pass_evid = (details[best_cat]["t"] + details[best_cat]["c"]) > 0
    
    # 3. Margin Gate with Tie-Breaker
    pass_margin = margin >= 1
    if margin == 0 and second_best_cat:
        # Check if tie broken by evidence density
        if details[best_cat]["t"] > details[second_best_cat]["t"]:
            pass_margin = True
        elif details[best_cat]["t"] == details[second_best_cat]["t"]:
            if details[best_cat]["c"] > details[second_best_cat]["c"]:
                pass_margin = True
    
    if pass_conf and pass_margin and pass_evid:
        return best_cat
        
    return "technology"


def map_category_id(title: str, content: str, category_map: dict[str, int] | None = None, source_name: str = "") -> int:
    """
    Dynamically maps articles to seeded PostgreSQL Category IDs based on keyword density and database IDs.
    """
    slug = map_category_slug(title, content, source_name)
    if category_map and slug in category_map:
        return category_map[slug]
    if category_map and "cybersecurity" in category_map and slug == "security":
        return category_map["cybersecurity"]
    if category_map:
        # Default to technology if available, else first item
        return category_map.get("technology", next(iter(category_map.values())))
    return 7



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
