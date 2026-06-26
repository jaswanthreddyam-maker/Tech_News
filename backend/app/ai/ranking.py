import math
import re
from datetime import datetime, timezone
from typing import Any


def compute_keyword_overlap(query: str, text: str) -> float:
    """
    Computes a simple Jaccard-like keyword overlap score between query and text.
    """
    if not query or not text:
        return 0.0

    query_tokens = set(re.findall(r"\w+", query.lower()))
    text_tokens = set(re.findall(r"\w+", text.lower()))

    if not query_tokens:
        return 0.0

    overlap = query_tokens.intersection(text_tokens)
    return len(overlap) / len(query_tokens)


def compute_freshness_score(published_at: datetime) -> float:
    """
    Computes exponential decay freshness score.
    Half-life of ~7 days.
    """
    if not published_at:
        return 0.0

    now = datetime.now(timezone.utc)
    delta = now - published_at
    days_old = max(0.0, delta.total_seconds() / 86400.0)

    # Exponential decay: e^(-lambda * t)
    # Let's use a 14-day scaling factor so at 14 days score is ~0.36
    return math.exp(-days_old / 14.0)


from app.models.article import ArticleReadModel


def rank_semantic_results(query: str, results: list[tuple[ArticleReadModel, float]]) -> list[dict[str, Any]]:
    """
    Applies the Hybrid Ranking Algorithm to a list of semantically similar articles.

    Formula:
    Score = (0.50 * Semantic) + (0.20 * Keyword) + (0.15 * Freshness) + (0.15 * Importance)

    Returns a sorted list of dictionaries with full scoring details.
    """
    ranked = []

    for article, semantic_score in results:
        # 1. Semantic (passed in)
        norm_semantic = max(0.0, min(1.0, semantic_score))

        # 2. Keyword Overlap (check title and summary)
        title_overlap = compute_keyword_overlap(query, article.title)
        summary_overlap = compute_keyword_overlap(query, article.summary or "")
        keyword_score = max(title_overlap, summary_overlap * 0.5)

        # 3. Freshness
        freshness_score = compute_freshness_score(article.published_at) if hasattr(article, "published_at") and article.published_at else 0.0

        # 4. Impact (formerly credibility/importance)
        impact_score = 0.0
        if hasattr(article, "final_score") and article.final_score is not None:
            impact_score = float(article.final_score)

        # Calculate Final Score (hardcode weights for now if settings aren't updated for impact)
        final_score = (
            (0.50 * norm_semantic)
            + (0.20 * keyword_score)
            + (0.15 * freshness_score)
            + (0.15 * impact_score)
        )

        ranked.append(
            {
                "article": article,
                "final_score": final_score,
                "components": {
                    "semantic": round(norm_semantic, 4),
                    "keyword": round(keyword_score, 4),
                    "freshness": round(freshness_score, 4),
                    "importance": round(impact_score, 4),
                },
            }
        )


    # Sort by final_score descending
    ranked.sort(key=lambda x: float(x["final_score"]), reverse=True)
    return ranked
