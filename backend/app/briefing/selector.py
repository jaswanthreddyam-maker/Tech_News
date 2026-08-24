import logging
import hashlib
import re
from typing import List, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleReadModel
from app.briefing.contracts import PRIMARY_QUALITY_FLOOR, EMERGENCY_QUALITY_FLOOR

logger = logging.getLogger(__name__)

# Stopwords for canonical title cluster hashing
_STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "and", "or", "but", "if", "then", "else", "when", "up", "out", "about",
    "new", "latest", "how", "why", "what", "who", "which", "this", "that"
}


def _compute_cluster_key(art: ArticleReadModel) -> str:
    """
    Computes a cross-source cluster key for an article to suppress duplicate coverage of the same event.
    Uses cluster_id if available; otherwise generates a hash from normalized title tokens (excluding source).
    """
    if hasattr(art, "cluster_id") and art.cluster_id:
        return str(art.cluster_id)

    # Clean title to lowercase alphanumeric words, filter stopwords
    clean_title = re.sub(r"[^\w\s]", "", (art.title or "").lower())
    words = [w for w in clean_title.split() if len(w) > 2 and w not in _STOPWORDS]
    sorted_words = sorted(set(words))
    key_str = "-".join(sorted_words[:6])
    if not key_str:
        key_str = clean_title[:30].strip()
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


class DailyBriefingSelector:
    """
    Rule-based, deterministic story selector for Daily Briefing.
    Applies minimum quality gating, cross-source cluster suppression, and soft diversity penalties.
    """

    @classmethod
    async def select_top_stories(
        cls, 
        db: AsyncSession, 
        limit: int = 10,
        cutoff_hours: int = 48
    ) -> List[ArticleReadModel]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=cutoff_hours)

        # 1. Primary Minimum Eligibility Gate (>= PRIMARY_QUALITY_FLOOR)
        stmt = (
            select(ArticleReadModel)
            .where(
                and_(
                    ArticleReadModel.is_test_data == False,
                    ArticleReadModel.publication_status == "PUBLISHED",
                    ArticleReadModel.published_at >= cutoff,
                    ArticleReadModel.final_score >= PRIMARY_QUALITY_FLOOR
                )
            )
            .order_by(ArticleReadModel.final_score.desc(), ArticleReadModel.published_at.desc())
            .limit(100)
        )
        res = await db.execute(stmt)
        candidates = list(res.scalars().all())

        # 2. Emergency Fallback Gate: If window has zero candidates, expand window but enforce EMERGENCY_QUALITY_FLOOR
        if not candidates:
            logger.info("BriefingSelector: Expanding cutoff window to recent published candidates >= emergency floor.")
            stmt_fb = (
                select(ArticleReadModel)
                .where(
                    and_(
                        ArticleReadModel.is_test_data == False,
                        ArticleReadModel.publication_status == "PUBLISHED",
                        ArticleReadModel.final_score >= EMERGENCY_QUALITY_FLOOR
                    )
                )
                .order_by(ArticleReadModel.final_score.desc(), ArticleReadModel.published_at.desc())
                .limit(50)
            )
            res_fb = await db.execute(stmt_fb)
            candidates = list(res_fb.scalars().all())

        if not candidates:
            logger.warning("BriefingSelector: No eligible candidate articles found above quality floors.")
            return []

        # 3. Story Cluster Suppression (1 representative story per event cluster)
        seen_clusters: Set[str] = set()
        clustered_candidates: List[ArticleReadModel] = []

        for art in candidates:
            ckey = _compute_cluster_key(art)
            if ckey not in seen_clusters:
                seen_clusters.add(ckey)
                clustered_candidates.append(art)

        # 4. Soft Diversity Selection with Score-Gap Preservation
        # Applies a 15% penalty per already-selected story in the same category,
        # but preserves selection if a candidate has a >20% raw score lead over lower-category alternatives.
        selected: List[ArticleReadModel] = []
        category_counts: Dict[str, int] = {}
        pool = list(clustered_candidates)

        while pool and len(selected) < limit:
            best_idx = 0
            best_adjusted_score = -1.0
            highest_raw_score = max(float(art.final_score or 0.0) for art in pool)

            for idx, art in enumerate(pool):
                base_score = float(art.final_score) if art.final_score is not None else 20.0
                cat = art.category or "Technology"
                cat_count = category_counts.get(cat, 0)

                # Soft diversity penalty (reduces effective score by 15% per existing story in same category)
                penalty_factor = 1.0 / (1.0 + (cat_count * 0.15))
                adjusted_score = base_score * penalty_factor

                # Score-gap preservation: if base score is >= 85% of pool max, preserve rank lead
                if base_score >= highest_raw_score * 0.85 and cat_count <= 2:
                    adjusted_score = max(adjusted_score, base_score * 0.90)

                if adjusted_score > best_adjusted_score:
                    best_adjusted_score = adjusted_score
                    best_idx = idx

            chosen_art = pool.pop(best_idx)
            selected.append(chosen_art)
            cat = chosen_art.category or "Technology"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        logger.info(
            f"BriefingSelector: Selected {len(selected)} stories from {len(candidates)} candidates "
            f"across {len(category_counts)} categories."
        )
        return selected
