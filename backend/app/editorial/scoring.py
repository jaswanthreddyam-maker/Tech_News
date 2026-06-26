import logging

from app.editorial.policy import PolicyLoader
from app.models.article import ProcessedArticle

logger = logging.getLogger("tech_news.editorial.scoring")


def calculate_impact_score(article: ProcessedArticle, entities: list[str]) -> float:
    """
    Calculates an editorial impact score (0.0 - 100.0) based on source authority,
    topic importance, named entities, breaking news flags, content quality, and reductions.
    """
    policy = PolicyLoader.get_policy()
    score = 40.0  # Base score

    # 1. Source Authority Boost
    source_name = (article.source or article.source_name or "").strip().lower()
    source_authority_policy = policy.get("source_authority", {})
    source_boost = 0.0
    for key, boost in source_authority_policy.items():
        if key.lower() in source_name:
            source_boost = max(source_boost, float(boost))
    score += source_boost

    # 2. Topic / Category Importance Boost
    topic_importance_policy = policy.get("topic_importance", {})
    category_slug = ""
    if article.category:
        category_slug = (article.category.slug or "").lower().replace("-", "_")

    topic_boost = float(topic_importance_policy.get(category_slug, topic_importance_policy.get("general", 5.0)))
    score += topic_boost

    # 3. Named Entity Importance (+5 per unique match, capped at +20)
    entity_importance_list = policy.get("entity_importance_list", [])
    entities_lower = {e.lower().strip() for e in entities}
    entity_matches = 0
    for target in entity_importance_list:
        if target.lower().strip() in entities_lower:
            entity_matches += 1

    entity_boost = min(20.0, entity_matches * 5.0)
    score += entity_boost

    # 4. Breaking News Bonus (+15)
    breaking_news_keywords = policy.get("breaking_news_keywords", [])
    title_lower = (article.title or "").lower()
    is_breaking = False
    for kw in breaking_news_keywords:
        if kw.lower() in title_lower:
            is_breaking = True
            break
    if is_breaking:
        score += 15.0

    # 5. Quality Bonus
    # Content length bonus
    content_len = len((article.content or "").split())
    if content_len >= 1000:
        score += 10.0
    elif content_len >= 500:
        score += 5.0

    # Thumbnail score quality bonus (+5 if thumbnail_score >= 80)
    if article.thumbnail_score is not None and article.thumbnail_score >= 80:
        score += 5.0

    # 6. Reductions (penalties added, reduction values are negative e.g. -20)
    reductions_policy = policy.get("reductions", {})
    content_lower = (article.content or "").lower()
    applied_reductions = 0.0
    for kw, penalty in reductions_policy.items():
        if kw.lower() in title_lower or kw.lower() in content_lower:
            applied_reductions += float(penalty)
    score += applied_reductions

    final_score = max(0.0, min(100.0, score))
    logger.debug(
        f"Scoring Article {article.id}: base=40, source={source_boost}, topic={topic_boost}, "
        f"entity={entity_boost}, breaking={15.0 if is_breaking else 0.0}, "
        f"len_boost={10.0 if content_len >= 1000 else (5.0 if content_len >= 500 else 0.0)}, "
        f"thumb_boost={5.0 if article.thumbnail_score and article.thumbnail_score >= 80 else 0.0}, "
        f"reductions={applied_reductions} -> final={final_score}"
    )
    return final_score
