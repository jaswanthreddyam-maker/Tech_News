import logging

logger = logging.getLogger("tech_news.editorial.diversity")


def apply_diversity_filter(
    candidates: list, article_topics: dict[str, list[str]], max_per_category: int = 3, max_total: int = 30
) -> tuple[list, list[tuple[any, str, dict]]]:
    """
    Applies categorical diversity rules to candidates.
    Allows at most `max_per_category` articles from the same category during the first pass.
    If total slots are not filled, backfills from the skipped candidates in descending score order.

    Returns:
        tuple containing:
        - List of selected articles
        - List of tuples containing (article, reason_code, reason_details) for decision logging
    """
    selected = []
    skipped = []
    category_counts = {}

    # Track reasons for logs
    decisions = []

    # First Pass: Enforce category quotas
    for item in candidates:
        article = item["article"]
        topics = article_topics.get(article.id, [])
        # Determine primary category
        primary_cat = topics[0].lower().strip() if topics else "general"

        current_count = category_counts.get(primary_cat, 0)
        if current_count < max_per_category:
            category_counts[primary_cat] = current_count + 1
            selected.append(item)
            decisions.append(
                (
                    article,
                    "CATEGORY_BALANCE",
                    {
                        "primary_category": primary_cat,
                        "category_count_after": current_count + 1,
                        "effective_score": item["effective_score"],
                    },
                )
            )
        else:
            skipped.append(item)

    # Second Pass: Backfill skipped candidates to avoid leaving slots empty
    if len(selected) < max_total and skipped:
        logger.info(
            f"Diversity: Homepage slots not filled ({len(selected)}/{max_total}). "
            f"Backfilling from {len(skipped)} skipped candidates."
        )
        for item in skipped:
            if len(selected) >= max_total:
                break
            selected.append(item)
            article = item["article"]
            topics = article_topics.get(article.id, [])
            primary_cat = topics[0].lower().strip() if topics else "general"
            decisions.append(
                (
                    article,
                    "BACKFILL",
                    {
                        "primary_category": primary_cat,
                        "effective_score": item["effective_score"],
                        "reason": f"Category '{primary_cat}' exceeded limit, but added to fill homepage slots.",
                    },
                )
            )

    return selected, decisions
