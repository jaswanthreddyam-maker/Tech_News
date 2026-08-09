"""
Deterministic Document Classifier.
Fast weighted-scoring classifier for newsletters, live blogs, roundups, opinion columns, and reviews.
Runs before AI summarization with 0 latency and 0 API token cost.
"""

import re
from typing import Tuple

from app.schemas.ai_summary import DocumentType

# Weighted signal tables (pattern, weight)
NEWSLETTER_SIGNALS = [
    (r"\bwelcome to installer\b", 40),
    (r"\binstaller no\b", 35),
    (r"\bthis week's installer\b", 30),
    (r"\bwelcome back\b", 25),
    (r"\bin this week's\b", 20),
    (r"\bthe drop\b", 20),
    (r"\bsigning off\b", 15),
    (r"\bsee you next week\b", 15),
    (r"\bcommunity picks\b", 15),
    (r"\bcrowdsourced\b", 15),
    (r"\bnewsletter\b", 20),
]

ROUNDUP_SIGNALS = [
    (r"\bweekly roundup\b", 40),
    (r"\bhere's what else\b", 25),
    (r"\btop picks\b", 25),
    (r"\bthis week's recommendations\b", 25),
    (r"\bbest apps of the week\b", 25),
    (r"\btech roundup\b", 30),
]

LIVE_BLOG_SIGNALS = [
    (r"\blive updates\b", 40),
    (r"\bminute-by-minute\b", 35),
    (r"\blive coverage\b", 35),
    (r"\bupdated in real-time\b", 30),
]

OPINION_SIGNALS = [
    (r"\bin my opinion\b", 35),
    (r"\bmy take\b", 35),
    (r"\bcolumn:\b", 30),
    (r"\bperspectives\b", 20),
]

REVIEW_SIGNALS = [
    (r"\bour verdict\b", 40),
    (r"\bhands-on review\b", 35),
    (r"\breview:\b", 30),
    (r"\btech review\b", 25),
]


def _compute_score(text: str, signals: list[Tuple[str, int]]) -> int:
    score = 0
    for pattern, weight in signals:
        if re.search(pattern, text):
            score += weight
    return score


def detect_document_type(
    title: str,
    content: str,
    category: str | None = None,
    tags: str | None = None
) -> Tuple[DocumentType | None, float]:
    """
    Returns (detected_document_type, confidence_score).
    Calculates weighted confidence based on structural text signals, category, and tags.
    """
    text_lower = f"{title}\n{content[:4000]}".lower()
    cat_lower = (category or "").lower()
    tags_lower = (tags or "").lower()

    # 1. Newsletter
    nl_score = _compute_score(text_lower, NEWSLETTER_SIGNALS)
    if "newsletter" in cat_lower:
        nl_score += 40
    if "newsletter" in tags_lower:
        nl_score += 25
    if nl_score >= 35:
        confidence = min(0.99, round(0.60 + (nl_score / 100.0) * 0.40, 2))
        return (DocumentType.NEWSLETTER, confidence)

    # 2. Live Blog
    lb_score = _compute_score(text_lower, LIVE_BLOG_SIGNALS)
    if "liveblog" in cat_lower or "liveblog" in tags_lower:
        lb_score += 40
    if lb_score >= 30:
        confidence = min(0.99, round(0.60 + (lb_score / 100.0) * 0.40, 2))
        return (DocumentType.LIVE_BLOG, confidence)

    # 3. Weekly Roundup
    rd_score = _compute_score(text_lower, ROUNDUP_SIGNALS)
    if "roundup" in cat_lower:
        rd_score += 40
    if "roundup" in tags_lower:
        rd_score += 25
    if rd_score >= 30:
        confidence = min(0.99, round(0.60 + (rd_score / 100.0) * 0.40, 2))
        return (DocumentType.ROUNDUP, confidence)

    # 4. Opinion
    op_score = _compute_score(text_lower, OPINION_SIGNALS)
    if "opinion" in cat_lower:
        op_score += 40
    if "opinion" in tags_lower:
        op_score += 25
    if op_score >= 30:
        confidence = min(0.99, round(0.60 + (op_score / 100.0) * 0.40, 2))
        return (DocumentType.OPINION, confidence)

    # 5. Review
    rv_score = _compute_score(text_lower, REVIEW_SIGNALS)
    if "review" in cat_lower:
        rv_score += 40
    if "review" in tags_lower:
        rv_score += 25
    if rv_score >= 30:
        confidence = min(0.99, round(0.60 + (rv_score / 100.0) * 0.40, 2))
        return (DocumentType.REVIEW, confidence)

    return (None, 0.0)
