"""
Contracts, taxonomy constants, and quality thresholds for Daily Briefing.
"""

from typing import List, Dict, Set

# ---------------------------------------------------------------------------
# Quality Floors
# ---------------------------------------------------------------------------
PRIMARY_QUALITY_FLOOR: float = 15.0
EMERGENCY_QUALITY_FLOOR: float = 10.0

# Maximum items a global canonical edition ever contains
EDITION_MAX_CAPACITY: int = 10

# ---------------------------------------------------------------------------
# Topic Taxonomy Mapping
# ---------------------------------------------------------------------------
TOPIC_TO_CATEGORIES: Dict[str, List[str]] = {
    "artificial-intelligence": [
        "artificial-intelligence", "ai", "machine-learning", "machine learning",
        "deep-learning", "llm", "generative-ai"
    ],
    "technology": [
        "technology", "software", "software-development", "cloud",
        "open-source", "developer-tools"
    ],
    "cybersecurity": [
        "cybersecurity", "security", "infosec", "privacy", "crypto-security", "vulnerability"
    ],
    "hardware": [
        "hardware", "semiconductors", "chips", "robotics", "devices", "quantum"
    ],
    "startups-and-business": [
        "startups", "business", "venture", "finance", "markets", "enterprise"
    ],
    "science": [
        "science", "research", "aerospace", "biotech", "energy"
    ],
}

VALID_TOPICS: Set[str] = set(TOPIC_TO_CATEGORIES.keys())


def normalize_category(cat: str | None) -> str:
    """Normalize article category to a lowercase slug."""
    if not cat:
        return "technology"
    return cat.strip().lower().replace(" ", "-").replace("_", "-")


def matches_preferred_topics(article_category: str | None, preferred_topics: List[str]) -> bool:
    """
    Check if an article's category matches any of the user's preferred topics.
    """
    if not preferred_topics:
        return True
    norm_cat = normalize_category(article_category)
    for topic in preferred_topics:
        allowed = TOPIC_TO_CATEGORIES.get(topic, [topic])
        for variant in allowed:
            if variant in norm_cat or norm_cat in variant:
                return True
    return False
