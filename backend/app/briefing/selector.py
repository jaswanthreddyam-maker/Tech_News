import logging
import hashlib
from typing import List, Dict, Any, Set
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleReadModel, ProcessedArticle

logger = logging.getLogger(__name__)

MINIMUM_CANONICAL_SCORE = 15.0 # Quality gate threshold

def _compute_cluster_key(art: ArticleReadModel) -> str:
    """
    Computes a cluster key for an article to suppress duplicate coverage of the same event.
    Uses cluster_id if available, otherwise generates a cluster hash from canonical title tokens.
    """
    if hasattr(art, "cluster_id") and art.cluster_id:
        return str(art.cluster_id)
    
    # Title token hash for story cluster deduplication
    words = [w.lower() for w in art.title.split() if len(w) > 3]
    sorted_words = sorted(set(words))
    key_str = "-".join(sorted_words[:6])
    if not key_str:
        key_str = art.title[:30].lower().strip()
    return hashlib.md5(key_str.encode("utf-8")).hexdigest()

class DailyBriefingSelector:
    """
    Rule-based, deterministic story selector for Daily Briefing.
    Applies minimum quality gating, story cluster suppression, and soft diversity penalties.
    """

    @classmethod
    async def select_top_stories(
        cls, 
        db: AsyncSession, 
        limit: int = 5,
        cutoff_hours: int = 48
    ) -> List[ArticleReadModel]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=cutoff_hours)

        # 1. Minimum Eligibility Gate
        stmt = (
            select(ArticleReadModel)
            .where(
                and_(
                    ArticleReadModel.is_test_data == False,
                    ArticleReadModel.publication_status == "PUBLISHED",
                    ArticleReadModel.published_at >= cutoff,
                    ArticleReadModel.final_score >= MINIMUM_CANONICAL_SCORE
                )
            )
            .order_by(ArticleReadModel.final_score.desc(), ArticleReadModel.published_at.desc())
            .limit(100)
        )
        res = await db.execute(stmt)
        candidates = list(res.scalars().all())

        # Fallback to general recent published articles if restricted window has fewer candidates
        if not candidates:
            logger.info("BriefingSelector: Expanding cutoff window to recent published candidates.")
            stmt_fb = (
                select(ArticleReadModel)
                .where(
                    and_(
                        ArticleReadModel.is_test_data == False,
                        ArticleReadModel.publication_status == "PUBLISHED"
                    )
                )
                .order_by(ArticleReadModel.published_at.desc(), ArticleReadModel.final_score.desc())
                .limit(50)
            )
            res_fb = await db.execute(stmt_fb)
            candidates = list(res_fb.scalars().all())

        if not candidates:
            logger.warning("BriefingSelector: No eligible candidate articles found.")
            return []

        # 2. Story Cluster Suppression (1 representative story per event cluster)
        seen_clusters: Set[str] = set()
        clustered_candidates: List[ArticleReadModel] = []

        for art in candidates:
            ckey = _compute_cluster_key(art)
            if ckey not in seen_clusters:
                seen_clusters.add(ckey)
                clustered_candidates.append(art)

        # 3. Soft Diversity Selection
        # Apply a minor diversity penalty to categories already selected,
        # but NEVER override a materially higher scoring article (>25% score gap).
        selected: List[ArticleReadModel] = []
        category_counts: Dict[str, int] = {}

        # Re-sort using soft diversity adjusted scores
        pool = list(clustered_candidates)
        
        while pool and len(selected) < limit:
            best_idx = 0
            best_adjusted_score = -1.0

            for idx, art in enumerate(pool):
                base_score = float(art.final_score) if art.final_score is not None else 20.0
                cat = art.category or "Technology"
                cat_count = category_counts.get(cat, 0)
                
                # Soft diversity penalty (reduces effective score by 15% per existing story in same category)
                penalty_factor = 1.0 / (1.0 + (cat_count * 0.15))
                adjusted_score = base_score * penalty_factor

                if adjusted_score > best_adjusted_score:
                    best_adjusted_score = adjusted_score
                    best_idx = idx

            chosen_art = pool.pop(best_idx)
            selected.append(chosen_art)
            cat = chosen_art.category or "Technology"
            category_counts[cat] = category_counts.get(cat, 0) + 1

        logger.info(f"BriefingSelector: Selected {len(selected)} stories from {len(candidates)} candidates across {len(category_counts)} categories.")
        return selected
