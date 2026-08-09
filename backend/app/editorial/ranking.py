import logging
from datetime import timezone

from app.editorial.policy import PolicyLoader

logger = logging.getLogger("tech_news.editorial.ranking")


def get_source_authority_rank(source_name: str, source_authority_policy: dict) -> int:
    """
    Returns rank category: High (3), Medium (2), Low (1), Unknown (0)
    based on the configured source authority scores.
    """
    if not source_name:
        return 0

    source_lower = source_name.lower().strip()
    max_score = 0.0
    for key, val in source_authority_policy.items():
        if key.lower() in source_lower:
            max_score = max(max_score, float(val))

    if max_score >= 30.0:
        return 3
    elif max_score >= 20.0:
        return 2
    elif max_score >= 10.0:
        return 1
    return 0


def sort_candidates_deterministically(candidates: list) -> list:
    """
    Sorts candidate articles deterministically.
    Sort key is: (-effective_score, -impact_score, -source_authority_rank, published_at_timestamp, article_id)

    Each item in candidates should be a dictionary:
    {
        "article": ArticleReadModel,
        "effective_score": float,
        "impact_score": float
    }
    """
    policy = PolicyLoader.get_policy()
    source_auth = policy.get("source_authority", {})

    def get_sort_key(item):
        art = item["article"]
        eff_score = float(item["effective_score"])
        imp_score = float(item["impact_score"])

        # Calculate source authority rank
        src_name = getattr(art, "source", "") or ""
        src_rank = get_source_authority_rank(src_name, source_auth)

        # Published at timestamp (default to 0 if missing)
        pub_ts = 0.0
        if art.published_at:
            if art.published_at.tzinfo is None:
                pub_ts = art.published_at.replace(tzinfo=timezone.utc).timestamp()
            else:
                pub_ts = art.published_at.timestamp()

        art_id = str(art.id)

        # Sort key:
        # 1. -eff_score_band (5-point buckets) so source authority can act as a tiebreaker for similar scores
        # 2. -src_rank (descending source authority)
        # 3. -eff_score (exact score for exact ordering within same authority)
        # 4. -imp_score
        # 5. pub_ts
        # 6. art_id
        eff_score_band = round(eff_score / 5.0) * 5.0
        return (-eff_score_band, -src_rank, -eff_score, -imp_score, pub_ts, art_id)

    candidates.sort(key=get_sort_key)
    return candidates
