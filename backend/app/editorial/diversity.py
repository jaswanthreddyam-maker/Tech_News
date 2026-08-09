import logging
from collections import defaultdict

from app.editorial.policy import PolicyLoader
from app.services.ingestion.filter import compute_title_similarity

logger = logging.getLogger("tech_news.editorial.diversity")


def apply_diversity_filter(
    candidates: list, article_topics: dict[str, list[str]], max_per_category: int = 3, max_total: int = 10
) -> tuple[list, list[tuple[any, str, dict]]]:
    """
    Applies multi-dimensional diversity rules to candidates.
    1. Publisher diversity (Hard cap per publisher)
    2. Category diversity (Hard cap per category)
    3. Topic deduplication (Remove highly similar titles)
    4. Backfill from skipped if slots are open.
    """
    policy_data = PolicyLoader.get_diversity_policy()
    div_cfg = policy_data.get("diversity", {})
    
    pub_cfg = div_cfg.get("publisher", {})
    cat_cfg = div_cfg.get("category", {})
    topic_cfg = div_cfg.get("topic_dedup", {})
    home_cfg = div_cfg.get("homepage", {})
    
    max_per_pub = pub_cfg.get("max_per_publisher", 3)
    max_per_cat = cat_cfg.get("max_per_category", 4)
    sim_thresh = topic_cfg.get("similarity_threshold", 0.65)
    total_slots = home_cfg.get("total_slots", max_total)

    selected = []
    skipped_pub = []
    skipped_cat = []
    skipped_dedup = []
    
    pub_counts = defaultdict(int)
    cat_counts = defaultdict(int)

    decisions = []

    # First Pass: Publisher, Category, and Dedup
    for item in candidates:
        article = item["article"]
        publisher = article.source or "unknown"
        topics = article_topics.get(article.id, [])
        primary_cat = topics[0].lower().strip() if topics else "general"

        # 1. Publisher Cap
        if pub_counts[publisher] >= max_per_pub:
            skipped_pub.append(item)
            decisions.append(
                (article, "PUBLISHER_CAP", {"publisher": publisher, "effective_score": item["effective_score"]})
            )
            continue

        # 2. Category Cap
        if cat_counts[primary_cat] >= max_per_cat:
            skipped_cat.append(item)
            decisions.append(
                (article, "CATEGORY_CAP", {"category": primary_cat, "effective_score": item["effective_score"]})
            )
            continue
            
        # 3. Topic Dedup
        is_duplicate = False
        for s_item in selected:
            s_article = s_item["article"]
            if compute_title_similarity(article.title, s_article.title) > sim_thresh:
                is_duplicate = True
                break
                
        if is_duplicate:
            skipped_dedup.append(item)
            decisions.append(
                (article, "TOPIC_DEDUP", {"effective_score": item["effective_score"]})
            )
            continue

        # Passes all filters
        pub_counts[publisher] += 1
        cat_counts[primary_cat] += 1
        selected.append(item)
        decisions.append(
            (article, "ACCEPTED", {"publisher": publisher, "category": primary_cat, "effective_score": item["effective_score"]})
        )
        
        if len(selected) >= total_slots:
            break

    # Second Pass: Backfill
    # Priority: Skipped Category -> Skipped Publisher (we want to preserve publisher diversity over category)
    if len(selected) < total_slots:
        for item in skipped_cat:
            if len(selected) >= total_slots:
                break
            # Still apply dedup during backfill
            article = item["article"]
            is_duplicate = False
            for s_item in selected:
                s_article = s_item["article"]
                if compute_title_similarity(article.title, s_article.title) > sim_thresh:
                    is_duplicate = True
                    break
            if not is_duplicate:
                selected.append(item)
                decisions.append(
                    (item["article"], "BACKFILL_CATEGORY", {"effective_score": item["effective_score"]})
                )

    if len(selected) < total_slots:
        for item in skipped_pub:
            if len(selected) >= total_slots:
                break
            article = item["article"]
            is_duplicate = False
            for s_item in selected:
                s_article = s_item["article"]
                if compute_title_similarity(article.title, s_article.title) > sim_thresh:
                    is_duplicate = True
                    break
            if not is_duplicate:
                selected.append(item)
                decisions.append(
                    (item["article"], "BACKFILL_PUBLISHER", {"effective_score": item["effective_score"]})
                )

    # Note: Skipped Dedup items are NEVER backfilled. If it's a duplicate story, we don't want it.

    return selected, decisions
