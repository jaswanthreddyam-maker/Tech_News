import logging
import re
from typing import Any

logger = logging.getLogger("tech_news.filter")

# Core Tech Ingestion Keywords
TECH_KEYWORDS = {
    r"\bai\b",
    r"\bllm\b",
    r"\bgpt\b",
    r"artificial\s+intelligence",
    r"machine\s+learning",
    r"deep\s+learning",
    r"neural\s+network",
    r"robot",
    r"robotic",
    r"humanoid",
    r"autonomous",
    r"startup",
    r"funding",
    r"venture\s+capital",
    r"seed\s+round",
    r"series\s+[a-z0-9]",
    r"cybersecurity",
    r"vulnerability",
    r"malware",
    r"ransomware",
    r"exploit",
    r"zero-day",
    r"software",
    r"open-source",
    r"github",
    r"developer",
    r"cloud\s+computing",
    r"database",
    r"quantum",
    r"semiconductor",
    r"gpu",
    r"nvidia",
    r"microchip",
    r"supercomputer",
    r"bio-tech",
    r"space-tech",
    r"fusion",
    r"clean-tech",
}

SPAM_KEYWORDS = {
    r"porn",
    r"casino",
    r"lottery",
    r"viagra",
    r"cryptocurrency\s+giveaway",
    r"free\s+tokens",
    r"discount\s+shoes",
    r"cheap\s+flights",
}

# Stop words for cheap-checks title overlap optimization
STOP_WORDS = {
    "by",
    "of",
    "on",
    "for",
    "with",
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "is",
    "are",
    "was",
    "officially",
    "announces",
    "announced",
    "announcement",
    "unveils",
    "unveiled",
    "launches",
    "launched",
    "releases",
    "released",
    "introducing",
    "introduced",
    "new",
    "update",
    "updates",
}


def normalize_title(title: str) -> str:
    """
    Strips standard site branding suffixes and normalizes whitespace/casing.
    """
    if not title:
        return ""
    title = title.strip()
    # Strip site branding suffixes (case-insensitive)
    branding_suffixes = [
        r"\s*-\s*techcrunch\b",
        r"\s*\|\s*the\s*verge\b",
        r"\s*\|\s*hacker\s*news\b",
        r"\s*-\s*openai\b",
        r"\s*-\s*anthropic\b",
        r"\s*-\s*nvidia\b",
        r"\s*-\s*deepmind\b",
        r"\s*\|\s*ars\s*technica\b",
        r"\s*\|\s*reddit\b",
    ]
    for suffix in branding_suffixes:
        title = re.sub(suffix, "", title, flags=re.IGNORECASE)
    # Remove special chars and normalize spaces
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"\s+", " ", title).strip().lower()
    return title


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein edit distance between two strings.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def compute_title_similarity(title1: str, title2: str) -> float:
    """
    Highly optimized multi-signal title similarity calculator (Cheap-Checks-First).
    1. Cheap Check: Normalize titles. If equal, return 1.0.
    2. Medium Check: Non-stop-word overlap (Jaccard).
       - If overlap < 0.25, return overlap (no duplicate).
       - If overlap >= 0.85, return 1.0 (duplicate).
    3. Expensive Check: Levenshtein distance fallback (only run on borderline overlap).
    """
    # 1. Normalize
    t1 = normalize_title(title1)
    t2 = normalize_title(title2)

    if not t1 or not t2:
        return 0.0
    if t1 == t2:
        return 1.0

    # 2. Token Overlap Check (Filter stop words)
    words1 = set(w for w in t1.split() if w not in STOP_WORDS)
    words2 = set(w for w in t2.split() if w not in STOP_WORDS)
    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)
    overlap = len(intersection) / len(union)

    # Fast path returns based on overlap certainty bounds
    if overlap < 0.25:
        return overlap
    if overlap >= 0.85:
        return 1.0

    # 3. Levenshtein fallback
    distance = levenshtein_distance(t1, t2)
    max_len = max(len(t1), len(t2), 1)
    edit_sim = 1.0 - (distance / max_len)

    # Combined score
    score = 0.6 * overlap + 0.4 * edit_sim
    return score


def evaluate_relevance(title: str, content: str) -> bool:
    """
    Perform pre-AI keyword relevance matching.
    Checks for high density of tech topics and filters out spam/non-relevant streams.
    """
    combined_text = f"{title} {content}".lower()

    # 1. Reject explicit spam
    for spam_pattern in SPAM_KEYWORDS:
        if re.search(spam_pattern, combined_text):
            logger.info(f"Relevance Filter: Rejected due to spam match '{spam_pattern}'")
            return False

    # 2. Count technical keyword mentions
    match_count = 0
    for tech_pattern in TECH_KEYWORDS:
        if re.search(tech_pattern, combined_text):
            match_count += 1
            if match_count >= 2:  # Require at least 2 distinct technical topic matches to pass filter
                return True

    # 3. Fail if too low relevance count
    logger.info(
        f"Relevance Filter: Rejected article '{title}' - failed tech keyword matching density (matches: {match_count})"
    )
    return False


def evaluate_adaptive_quality(title: str, content: str, raw_html: str, meta_dict: dict) -> dict[str, Any]:
    """
    Deep adaptive content quality pipeline and extraction confidence analyzer.
    Returns scoring, confidence rating (0-100) and eligibility status.
    """
    # 1. Base validation
    if not content or not title:
        return {"eligible": False, "confidence": 0.0, "reason": "Empty title or body content."}

    words = content.lower().split()
    total_words = len(words)
    if total_words < 80:
        # Legitimate short flashes (minimum 25 words) from official or editorial sources
        is_trusted = meta_dict.get("source_category") in ("official", "editorial")
        if not is_trusted or total_words < 25:
            return {
                "eligible": False,
                "confidence": 0.0,
                "reason": f"Insufficient content length ({total_words} words).",
            }

    # 2. Unique Token Ratio (Spam/Repeating markup detection)
    unique_words = len(set(words))
    unique_ratio = unique_words / total_words if total_words > 0 else 0.0

    # 3. Truncation and Ellipsis Checks (Snippet detection)
    truncated = False
    truncation_reason = ""
    clean_text_lower = content.lower().strip()

    # Ellipsis at end
    if (
        clean_text_lower.endswith("...")
        or clean_text_lower.endswith("…")
        or clean_text_lower.endswith("[...]")
        or clean_text_lower.endswith("[…]")
    ):
        truncated = True
        truncation_reason = "Trailing truncation ellipsis"

    # Snippet boilerplate
    truncation_re = r"\b(read\s+more|continue\s+reading|read\s+the\s+full\s+article|subscribe\s+to\s+unlock|register\s+to\s+read|read\s+full\s+story)\b"
    if re.search(truncation_re, clean_text_lower):
        truncated = True
        truncation_reason = "Truncation/paywall boilerplate match"

    # 4. Markup/Junk Ratio (Text content vs HTML bloat)
    html_len = len(raw_html) if raw_html else 1
    markup_ratio = len(content) / html_len

    # 5. Paragraph Count
    paragraphs = [p for p in content.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs)

    # Rejection conditions
    if unique_ratio < 0.35 and total_words > 100:
        return {
            "eligible": False,
            "confidence": 0.0,
            "reason": f"Extremely low unique token ratio ({unique_ratio:.2f}) - likely spam/boilerplate.",
        }
    if truncated and total_words < 120:
        return {
            "eligible": False,
            "confidence": 0.0,
            "reason": f"Truncated snippet or paywall feed detected: {truncation_reason}.",
        }

    # 6. Extraction Confidence Score (0.0 to 1.0 Normalized)
    # parsing score: 1.0 if successfully parsed, 0.5 if fallback used
    s_parsing = 0.5 if meta_dict.get("rss_fallback", False) else 1.0

    # density score: normalized word density
    s_density = min(1.0, total_words / 350.0)

    # truncation score: 0.0 if truncated snippet, 1.0 if complete
    s_truncation = 0.2 if truncated else 1.0

    # metadata score: check presence of standard tags/authors/readability indices
    meta_present_count = sum(1 for k in ["author", "publish_date", "seo_keywords"] if meta_dict.get(k))
    s_metadata = min(1.0, (meta_present_count + 1) / 4.0)

    # Normalized score: 0.3 parsing + 0.3 density + 0.3 truncation + 0.1 metadata
    confidence_score = 0.3 * s_parsing + 0.3 * s_density + 0.3 * s_truncation + 0.1 * s_metadata

    # Penalties
    if paragraph_count < 2:
        confidence_score -= 0.15
    if markup_ratio < 0.02:  # Extremely bloated HTML page with very little content
        confidence_score -= 0.10

    confidence_percentage = round(max(0.0, min(1.0, confidence_score)) * 100.0, 1)

    return {
        "eligible": True,
        "confidence": confidence_percentage,
        "readability": int(confidence_percentage * 0.9),  # Proxy proxy index
        "paragraph_count": paragraph_count,
        "unique_ratio": round(unique_ratio, 2),
        "markup_ratio": round(markup_ratio, 3),
    }


def check_pre_ai_ingestion_eligibility(
    title: str, content: str, source_credibility: int, min_credibility_threshold: int = 40
) -> bool:
    """
    Unified validation routine checking article quality before queueing for AI summarization.
    """
    # 1. Skip if source is untrusted or disabled
    if source_credibility < min_credibility_threshold:
        logger.warning(
            f"Ingestion Eligibility: Rejected due to low source credibility ({source_credibility} < {min_credibility_threshold})"
        )
        return False

    # 2. Check minimal title and content length
    if not title or len(title) < 10:
        logger.warning("Ingestion Eligibility: Rejected due to empty or too short title.")
        return False

    if not content or len(content) < 100:
        logger.warning("Ingestion Eligibility: Rejected due to insufficient article body density.")
        return False

    # 3. Check tech content relevance
    return evaluate_relevance(title, content)
