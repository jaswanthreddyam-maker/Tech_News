import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.editorial.diversity import apply_diversity_filter
from app.editorial.freshness import calculate_freshness_multiplier
from app.editorial.models import EditorialDecisionLog
from app.editorial.ranking import sort_candidates_deterministically
from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import ArticleTopicLink

logger = logging.getLogger("tech_news.editorial.homepage_builder")


class HomepageBuilder:
    @staticmethod
    async def build_homepage(
        db: AsyncSession, category_filter: str | None = None, log_decisions: bool = False
    ) -> list[ArticleReadModel]:
        """
        Builds the ranked, curated, and category-diversified homepage feed.
        This function is strictly read-only by default (no DB writes or commits),
        unless `log_decisions` is set to True (which runs in Celery background/hourly).
        """
        now = datetime.now(timezone.utc)
        cutoff_hours = getattr(settings, "EDITORIAL_WINDOW_HOURS", 24)
        cutoff = now - timedelta(hours=cutoff_hours)

        # 1. Fetch candidates published in the last 24h (deferring large columns for performance)
        from sqlalchemy.orm import defer
        stmt = select(ArticleReadModel).where(
            ArticleReadModel.is_test_data == False, ArticleReadModel.published_at >= cutoff
        ).options(
            defer(ArticleReadModel.content),
            defer(ArticleReadModel.summary),
            defer(ArticleReadModel.embedding)
        )
        res = await db.execute(stmt)
        articles = res.scalars().all()

        if not articles:
            logger.info("HomepageBuilder: No candidate articles found in the last 24h.")
            return []

        # 2. Fetch all topic links for these candidates in one batch using a join and selecting only columns
        topic_stmt = select(ArticleTopicLink.article_id, ArticleTopicLink.topic_name).join(
            ArticleReadModel, ArticleReadModel.id == ArticleTopicLink.article_id
        ).where(
            ArticleReadModel.is_test_data == False, ArticleReadModel.published_at >= cutoff
        )
        topic_res = await db.execute(topic_stmt)

        article_topics = {}
        for row in topic_res.all():
            article_topics.setdefault(row[0], []).append(row[1])

        # 3. Calculate freshness multiplier and effective score
        decay_model = getattr(settings, "FRESHNESS_DECAY_MODEL", "curved")
        min_eff_score = getattr(settings, "MINIMUM_EFFECTIVE_SCORE", 20.0)

        candidates = []
        for art in articles:
            # Enforce timezone safety
            pub_at = art.published_at
            if pub_at.tzinfo is None:
                pub_at = pub_at.replace(tzinfo=timezone.utc)

            mult = calculate_freshness_multiplier(pub_at, decay_model=decay_model, window_hours=cutoff_hours, now=now)
            imp_score = float(art.final_score) if art.final_score is not None else 0.0
            eff_score = max(imp_score * mult, 1.0)  # floor at 1.0 so unscored articles still surface

            if eff_score >= min_eff_score:
                candidates.append(
                    {
                        "article": art,
                        "effective_score": eff_score,
                        "impact_score": imp_score,
                        "freshness_multiplier": mult,
                    }
                )

        if not candidates:
            logger.info(f"HomepageBuilder: Zero articles met the minimum effective score of {min_eff_score}. Returning all candidates unfiltered.")
            # Fallback: return all articles sorted by final_score so unscored articles surface
            fallback = sorted(articles, key=lambda a: float(a.final_score or 0), reverse=True)
            return fallback

        # 4. Sort candidates deterministically
        sorted_candidates = sort_candidates_deterministically(candidates)

        # 5. Apply category diversity filtering
        max_per_cat = getattr(settings, "MAX_ARTICLES_PER_CATEGORY", 3)
        max_total = getattr(settings, "MAX_HOMEPAGE_ARTICLES", 30)

        selected_items, decisions = apply_diversity_filter(
            sorted_candidates, article_topics, max_per_category=max_per_cat, max_total=max_total
        )

        final_articles = [item["article"] for item in selected_items]

        # Re-fetch full objects to avoid lazy-loading N+1 queries during serialization/logging
        if final_articles:
            final_ids = [art.id for art in final_articles]
            full_stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(final_ids))
            full_res = await db.execute(full_stmt)
            full_articles_map = {art.id: art for art in full_res.scalars().all()}
            
            # Maintain original sorted order and references
            final_articles = [full_articles_map[aid] for aid in final_ids if aid in full_articles_map]
            
            # Update selected_items with the fully loaded article objects
            for item in selected_items:
                art_id = item["article"].id
                if art_id in full_articles_map:
                    item["article"] = full_articles_map[art_id]

        # 6. Optionally log snapshots to database (e.g. hourly)
        if log_decisions and selected_items:
            snapshot_id = now.strftime("%Y%m%dT%H%M%SZ")
            algo_ver = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v1")

            # Create a lookup map for decisions reasons
            decision_map = {}
            for art, code, details in decisions:
                decision_map[art.id] = (code, details)

            try:
                for idx, item in enumerate(selected_items):
                    art = item["article"]
                    topics = article_topics.get(art.id, [])
                    primary_cat = topics[0].lower().strip() if topics else "general"
                    reason_code, reason_details = decision_map.get(art.id, ("HIGHEST_SCORE", {}))

                    log_entry = EditorialDecisionLog(
                        snapshot_id=snapshot_id,
                        article_id=str(art.id),
                        impact_score=item.get("impact_score", 0.0),
                        freshness_multiplier=item["freshness_multiplier"],
                        effective_score=item["effective_score"],
                        category=primary_cat,
                        ranking_position=idx + 1,
                        algorithm_version=algo_ver,
                        selection_reason_code=reason_code,
                        selection_reason_details=reason_details,
                    )
                    db.add(log_entry)

                await db.commit()
                logger.info(f"HomepageBuilder: Successfully persisted decision log snapshot ID {snapshot_id}.")
            except Exception as e:
                logger.error(f"HomepageBuilder: Failed to persist decision logs: {e}")
                # Don't fail the build if logging fails, but rollback transaction
                await db.rollback()

        # 7. Apply optional category filter on final curated list
        if category_filter:
            filtered_articles = []
            category_filter_lower = category_filter.lower().strip()
            for art in final_articles:
                topics = article_topics.get(art.id, [])
                if any(category_filter_lower in t.lower() for t in topics):
                    filtered_articles.append(art)
            return filtered_articles

        return final_articles
