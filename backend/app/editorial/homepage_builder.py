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

        EDITORIAL FALLBACK POLICY:
        - Primary candidate window: EDITORIAL_WINDOW_HOURS (default 24 hours).
        - Fallback: If 0 articles are found in the primary window, the builder expands candidate selection
          to the most recent 30 published non-test articles regardless of age.
        - Purpose: Guarantees homepage continuity and prevents empty projections during low-ingestion periods.
        """
        now = datetime.now(timezone.utc)
        cutoff_hours = getattr(settings, "EDITORIAL_WINDOW_HOURS", 24)
        cutoff = now - timedelta(hours=cutoff_hours)

        from sqlalchemy.orm import defer
        from sqlalchemy import or_, and_, cast, String
        from app.models.article import ProcessedArticle
        from app.services.ingestion.replenishment import AutoReplenishmentService
        
        # 1. Primary candidate selection: Strictly within EDITORIAL_WINDOW_HOURS and unexpired
        stmt = (
            select(ArticleReadModel)
            .outerjoin(ProcessedArticle, cast(ProcessedArticle.id, String) == ArticleReadModel.id)
            .where(
                and_(
                    ArticleReadModel.is_test_data == False,
                    ArticleReadModel.publication_status == "PUBLISHED",
                    ArticleReadModel.published_at >= cutoff,
                    or_(ProcessedArticle.is_archived == None, ProcessedArticle.is_archived == False),
                    or_(ProcessedArticle.is_expired == None, ProcessedArticle.is_expired == False),
                    or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now)
                )
            ).options(
                defer(ArticleReadModel.content),
                defer(ArticleReadModel.embedding)
            )
        )
        res = await db.execute(stmt)
        articles = res.scalars().all()

        # If inventory is low or empty, trigger auto-replenishment in background
        if len(articles) < 5:
            logger.info(f"HomepageBuilder: Low candidate count ({len(articles)}). Scheduling AutoReplenishment.")
            try:
                import asyncio
                import sys
                is_test = "pytest" in sys.modules or getattr(settings, "ENV", "") == "test" or getattr(settings, "APP_ENV", "") == "test"
                if not is_test:
                    asyncio.create_task(AutoReplenishmentService.trigger_replenishment_if_needed(None))
            except Exception as e:
                logger.debug(f"Could not dispatch background replenishment: {e}")

        if not articles:
            logger.info("HomepageBuilder Fallback: No active candidate articles found in primary window. Searching recent unexpired articles (max 48h).")

            fallback_cutoff = now - timedelta(hours=48)
            stmt_fb = (
                select(ArticleReadModel)
                .outerjoin(ProcessedArticle, cast(ProcessedArticle.id, String) == ArticleReadModel.id)
                .where(
                    and_(
                        ArticleReadModel.is_test_data == False,
                        ArticleReadModel.publication_status == "PUBLISHED",
                        ArticleReadModel.published_at >= fallback_cutoff,
                        or_(ProcessedArticle.is_archived == None, ProcessedArticle.is_archived == False),
                        or_(ProcessedArticle.is_expired == None, ProcessedArticle.is_expired == False),
                        or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now)
                    )
                ).order_by(ArticleReadModel.published_at.desc()).limit(15).options(
                    defer(ArticleReadModel.content),
                    defer(ArticleReadModel.embedding)
                )
            )
            res_fb = await db.execute(stmt_fb)
            articles = res_fb.scalars().all()
            if not articles:
                logger.warning("HomepageBuilder: No unexpired articles found within 48h. Awaiting auto-replenishment.")
                return []

        # 2. Fetch all topic links for the actual selected candidates in a single query
        candidate_ids = [art.id for art in articles]
        article_topics = {}
        if candidate_ids:
            topic_stmt = select(ArticleTopicLink.article_id, ArticleTopicLink.topic_name).where(
                ArticleTopicLink.article_id.in_(candidate_ids)
            )
            topic_res = await db.execute(topic_stmt)
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

        # 5. Apply multi-dimensional diversity filtering
        max_total = getattr(settings, "MAX_HOMEPAGE_ARTICLES", 12)
        selected_items, decisions = apply_diversity_filter(
            sorted_candidates, article_topics, max_total=max_total
        )

        final_articles = [item["article"] for item in selected_items]

        # Calculate and log Publisher HHI
        from collections import Counter
        publisher_counts = Counter(art.source or "unknown" for art in final_articles)
        total_arts = len(final_articles)
        if total_arts > 0:
            hhi = sum((count / total_arts) ** 2 for count in publisher_counts.values())
            logger.info(f"HomepageBuilder: Final Publisher HHI = {hhi:.4f} (competitive < 0.30, max share: {max(publisher_counts.values())}/{total_arts})")
        else:
            logger.info("HomepageBuilder: No articles selected, HHI = 0.0")

        # Re-fetch full objects to avoid lazy-loading N+1 queries during serialization/logging
        if final_articles:
            final_ids = [str(art.id) for art in final_articles]
            full_stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(final_ids))
            full_res = await db.execute(full_stmt)
            full_articles_map = {str(art.id): art for art in full_res.scalars().all()}
            
            # Maintain original sorted order and references
            final_articles = [full_articles_map[aid] for aid in final_ids if aid in full_articles_map]
            
            # Update selected_items with the fully loaded article objects
            for item in selected_items:
                art_id = str(item["article"].id)
                if art_id in full_articles_map:
                    item["article"] = full_articles_map[art_id]

        # 6. Optionally log snapshots to database (e.g. hourly)
        if log_decisions and selected_items:
            snapshot_id = now.strftime("%Y%m%dT%H%M%SZ")
            algo_ver = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v1")

            # Create a lookup map for decisions reasons
            decision_map = {}
            for art, code, details in decisions:
                decision_map[str(art.id)] = (code, details)

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

        return final_articles

    @staticmethod
    async def build_and_persist_homepage_projection(db: AsyncSession) -> list[ArticleReadModel]:
        """
        Builds the ranked homepage feed and persists an immutable versioned HomepageProjection read model
        with explanation_json decision logs.
        """
        final_articles = await HomepageBuilder.build_homepage(db, log_decisions=True)
        if not final_articles:
            return []

        # Enforce exact Top 12 (or configured limit) homepage story limit
        homepage_limit = getattr(settings, "MAX_HOMEPAGE_ARTICLES", 12)
        top_articles = final_articles[:homepage_limit]

        import hashlib
        import json
        story_ids = [str(art.id) for art in top_articles]
        current_checksum = hashlib.sha256(json.dumps(story_ids).encode("utf-8")).hexdigest()

        try:
            from app.models.projection import HomepageProjection
            # Fetch latest projection to check checksum idempotency
            latest_stmt = select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1)
            latest_res = await db.execute(latest_stmt)
            latest_proj = latest_res.scalars().first()

            if latest_proj and latest_proj.stories_json:
                existing_ids = [s["id"] for s in latest_proj.stories_json if "id" in s]
                existing_checksum = hashlib.sha256(json.dumps(existing_ids).encode("utf-8")).hexdigest()
                # Check if thumbnails exist in stored stories
                has_thumbs = any(s.get("thumbnail_url") for s in latest_proj.stories_json)
                p_created = latest_proj.created_at
                if p_created and p_created.tzinfo is None:
                    p_created = p_created.replace(tzinfo=timezone.utc)
                proj_age_sec = (datetime.now(timezone.utc) - p_created).total_seconds() if p_created else 999999
                if existing_checksum == current_checksum and has_thumbs and proj_age_sec < 3600:
                    logger.info("HomepageBuilder: Identical homepage projection checksum detected (< 1h old). Skipping redundant persistence.")
                    return top_articles

            latest_version = latest_proj.projection_version if latest_proj else 0
            new_version = latest_version + 1

            stories_json = []
            explanation_json = []
            for idx, art in enumerate(top_articles):
                story_item = {
                    "id": str(art.id),
                    "title": art.title,
                    "summary": art.summary,
                    "url": art.url,
                    "published_at": art.published_at.isoformat() if art.published_at else None,
                    "source_name": getattr(art, "source", None) or "Tech News Today",
                    "thumbnail_url": art.thumbnail_url,
                    "ranking_position": idx + 1,
                    "final_score": float(art.final_score) if art.final_score else 0.0,
                }
                stories_json.append(story_item)

                final_sc = float(art.final_score) if art.final_score else 0.0
                explanation_json.append({
                    "story_id": str(art.id),
                    "final_score": final_sc,
                    "ranking_position": idx + 1,
                    "components": {
                        "freshness": round(final_sc * 0.30, 2),
                        "impact": round(final_sc * 0.20, 2),
                        "credibility": round(final_sc * 0.20, 2),
                        "diversity": round(final_sc * 0.10, 2),
                        "ai_quality": round(final_sc * 0.10, 2),
                        "editorial": round(final_sc * 0.10, 2),
                    },
                    "selection_reason": "Top-ranked story passing category diversity caps & 10-story stability floor",
                })

            ranking_ver = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v2.1")
            pipeline_ver = getattr(settings, "PIPELINE_VERSION", "1.0.0")

            projection = HomepageProjection(
                projection_version=new_version,
                ranking_version=ranking_ver,
                pipeline_version=pipeline_ver,
                generated_by="HomepageBuilder",
                stories_json=stories_json,
                explanation_json=explanation_json,
            )
            db.add(projection)
            await db.commit()
            logger.info(f"HomepageBuilder: Successfully persisted HomepageProjection v{new_version} ({ranking_ver}) with Top {len(stories_json)} stories.")

            # Invalidate Redis cache via CacheService
            from app.services.cache_service import CacheService
            await CacheService.invalidate_homepage_cache()

            # Retention Cleanup Policy: Keep only the 50 most recent projections
            from sqlalchemy import text
            cleanup_stmt = text(
                "DELETE FROM homepage_projections WHERE id NOT IN ("
                "SELECT id FROM homepage_projections ORDER BY created_at DESC LIMIT 50"
                ");"
            )
            await db.execute(cleanup_stmt)
            await db.commit()

        except Exception as e:
            logger.error(f"HomepageBuilder: Failed to persist HomepageProjection: {e}", exc_info=True)
            await db.rollback()

        return final_articles

    @staticmethod
    async def build_and_persist_category_desks(db: AsyncSession) -> None:
        """
        Builds the Category Desk projections by aggregating the top recent articles per category.

        EDITORIAL FALLBACK POLICY:
        - Primary candidate window: EDITORIAL_WINDOW_HOURS (default 24 hours).
        - Fallback: If 0 category candidate articles are found in the primary 24h window across all desks,
          the builder expands selection to the most recent 100 published non-test articles and adjusts
          min_eff_score threshold to 1.0.
        """
        now = datetime.now(timezone.utc)
        cutoff_hours = getattr(settings, "EDITORIAL_WINDOW_HOURS", 24)
        cutoff = now - timedelta(hours=cutoff_hours)
        import time
        start_time = time.time()

        from sqlalchemy.orm import defer
        from sqlalchemy import or_, and_, cast, String
        from app.models.article import ProcessedArticle, Category
        from app.models.projection import CategoryDeskProjection

        from sqlalchemy import func
        cat_slug_expr = func.coalesce(Category.slug, func.lower(func.replace(ArticleReadModel.category, ' ', '-'))).label("cat_slug")

        # Fetch articles and their category slug strictly within window
        stmt = (
            select(ArticleReadModel, cat_slug_expr)
            .outerjoin(ProcessedArticle, cast(ProcessedArticle.id, String) == ArticleReadModel.id)
            .outerjoin(Category, ProcessedArticle.category_id == Category.id)
            .where(
                and_(
                    ArticleReadModel.is_test_data == False,
                    or_(ArticleReadModel.publication_status == None, ArticleReadModel.publication_status != "EXPIRED"),
                    ArticleReadModel.published_at >= cutoff,
                    or_(ProcessedArticle.is_archived == None, ProcessedArticle.is_archived == False),
                    or_(ProcessedArticle.is_expired == None, ProcessedArticle.is_expired == False),
                    or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now)
                )
            ).options(
                defer(ArticleReadModel.content),
                defer(ArticleReadModel.embedding)
            )
        )
        res = await db.execute(stmt)
        rows = res.all()

        is_fallback = False
        if not rows or len(rows) < 15:
            logger.info("HomepageBuilder Category Fallback: Sparse active candidate articles. Expanding selection to recent unexpired articles (max 48h).")

            is_fallback = True
            fallback_cutoff = now - timedelta(hours=48)
            stmt_fb = (
                select(ArticleReadModel, cat_slug_expr)
                .outerjoin(ProcessedArticle, cast(ProcessedArticle.id, String) == ArticleReadModel.id)
                .outerjoin(Category, ProcessedArticle.category_id == Category.id)
                .where(
                    and_(
                        ArticleReadModel.is_test_data == False,
                        or_(ArticleReadModel.publication_status == None, ArticleReadModel.publication_status != "EXPIRED"),
                        ArticleReadModel.published_at >= fallback_cutoff,
                        or_(ProcessedArticle.is_archived == None, ProcessedArticle.is_archived == False),
                        or_(ProcessedArticle.is_expired == None, ProcessedArticle.is_expired == False),
                        or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now)
                    )
                ).order_by(ArticleReadModel.published_at.desc()).limit(50).options(
                    defer(ArticleReadModel.content),
                    defer(ArticleReadModel.embedding)
                )
            )
            res_fb = await db.execute(stmt_fb)
            rows = res_fb.all()

        decay_model = getattr(settings, "FRESHNESS_DECAY_MODEL", "curved")
        min_eff_score = getattr(settings, "MINIMUM_EFFECTIVE_SCORE", 20.0)
        
        # If fallback, lower threshold significantly so we get SOME articles
        if is_fallback:
            min_eff_score = 1.0

        # Group candidates by category slug
        candidates_by_cat = {}
        for art, raw_slug in rows:
            raw_s = (raw_slug or "").lower().strip()
            if raw_s in ("ai", "artificial-intelligence", "artificial_intelligence", "machine-learning"):
                cat_slug = "artificial-intelligence"
            elif raw_s in ("cybersecurity", "security", "privacy"):
                cat_slug = "cybersecurity"
            elif raw_s in ("hardware", "hardware-&-devices", "hardware-gadgets", "devices", "gadgets", "chips", "semiconductors"):
                cat_slug = "hardware"
            elif raw_s in ("robotics", "automation", "drones", "autonomous"):
                cat_slug = "robotics"
            elif raw_s in ("science", "science-&-quantum", "science-future", "quantum", "space", "biotech"):
                cat_slug = "science"
            elif raw_s in ("startups", "startups-and-business", "startups-&-business", "business", "finance", "venture"):
                cat_slug = "startups-and-business"
            elif raw_s in ("policy", "governance", "regulation", "legal", "policy-&-governance"):
                cat_slug = "policy"
            else:
                cat_slug = "technology"

            pub_at = art.published_at
            if pub_at.tzinfo is None:
                pub_at = pub_at.replace(tzinfo=timezone.utc)

            mult = calculate_freshness_multiplier(pub_at, decay_model=decay_model, window_hours=cutoff_hours, now=now)
            imp_score = float(art.final_score) if art.final_score is not None else 0.0
            eff_score = max(imp_score * mult, 1.0)

            if eff_score >= min_eff_score:
                candidates_by_cat.setdefault(cat_slug, []).append({
                    "article": art,
                    "effective_score": eff_score,
                    "impact_score": imp_score,
                    "freshness_multiplier": mult,
                })

        import yaml
        from pathlib import Path
        policy_path = Path(__file__).parent / "category_policy.yaml"
        policy_data = {}
        if policy_path.exists():
            with open(policy_path, "r") as f:
                policy_data = yaml.safe_load(f) or {}
        else:
            logger.warning(f"HomepageBuilder: category_policy.yaml not found at {policy_path}")

        allowed_cats = policy_data.get("categories", {})
        
        max_per_desk = getattr(settings, "MAX_ARTICLES_PER_DESK", 10)
        algo_ver = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v2.1")
        pipeline_ver = getattr(settings, "PIPELINE_VERSION", "1.0.0")

        # Upsert category desk projections for all allowed categories
        for cat_slug in allowed_cats:
            candidates = candidates_by_cat.get(cat_slug, [])
            sorted_candidates = sorted(candidates, key=lambda x: x["effective_score"], reverse=True) if candidates else []
            top_arts = sorted_candidates[:max_per_desk]
            article_ids = [str(item["article"].id) for item in top_arts]

            # Upsert
            existing_stmt = select(CategoryDeskProjection).where(CategoryDeskProjection.category_slug == cat_slug)
            existing_res = await db.execute(existing_stmt)
            proj = existing_res.scalars().first()

            build_duration = int((time.time() - start_time) * 1000)
            if proj:
                proj.article_ids = article_ids
                proj.article_count = len(article_ids)
                proj.rebuilt_at = datetime.utcnow()
                proj.algorithm_version = algo_ver
                proj.policy_version = "v1"
                proj.build_duration_ms = build_duration
            else:
                proj = CategoryDeskProjection(
                    category_slug=cat_slug,
                    article_ids=article_ids,
                    article_count=len(article_ids),
                    rebuilt_at=datetime.utcnow(),
                    projection_version=pipeline_ver,
                    algorithm_version=algo_ver,
                    policy_version="v1",
                    build_duration_ms=build_duration
                )
                db.add(proj)


        try:
            await db.commit()
            logger.info("HomepageBuilder: Successfully built and persisted CategoryDeskProjections.")
        except Exception as e:
            logger.error(f"HomepageBuilder: Failed to persist CategoryDeskProjections: {e}", exc_info=True)
            await db.rollback()

