import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.article import ProcessedArticle
from app.models.behavioral import ReadingSession, UserInterest
from app.schemas.recommendations import RecommendationReason, RecommendationResponse


class RecommendationStrategy(ABC):
    @abstractmethod
    async def recommend(self, session: AsyncSession, user_id: int | None, anonymous_id: str | None, limit: int) -> list[RecommendationResponse]:
        pass

class Candidate:
    def __init__(self, article: ProcessedArticle):
        self.article = article
        self.similarity_score = 0.0
        self.freshness_score = 0.0
        self.editorial_score = 0.0
        self.trending_score = 0.0
        self.novelty_score = 0.0
        self.diversity_penalty = 0.0
        self.final_score = 0.0
        self.confidence = 0.0
        self.dominant_interest = None

    def calculate_final(self):
        self.final_score = (
            settings.REC_WEIGHT_SIMILARITY * self.similarity_score +
            settings.REC_WEIGHT_FRESHNESS * self.freshness_score +
            settings.REC_WEIGHT_EDITORIAL * self.editorial_score +
            settings.REC_WEIGHT_TRENDING * self.trending_score +
            settings.REC_WEIGHT_NOVELTY * self.novelty_score
        ) - self.diversity_penalty

class BehavioralStrategy(RecommendationStrategy):
    async def recommend(self, session: AsyncSession, user_id: int | None, anonymous_id: str | None, limit: int) -> list[RecommendationResponse]:
        interests = await self._get_interests(session, user_id, anonymous_id)
        if not interests:
            return [] # Fallback required

        read_ids = await self._get_read_history(session, user_id, anonymous_id)

        candidates = await self._retrieve_candidates(session, interests, read_ids)
        candidates = await self._expand_candidates(session, candidates, read_ids)
        candidates = self._filter_eligibility(candidates, read_ids)

        self._score_candidates(candidates, interests)
        self._apply_freshness(candidates)
        self._apply_diversity(candidates)

        candidates.sort(key=lambda c: c.final_score, reverse=True)
        top_candidates = candidates[:limit]

        return [self._explain(c) for c in top_candidates]

    async def _get_interests(self, session: AsyncSession, user_id: int | None, anonymous_id: str | None) -> list[UserInterest]:
        stmt = select(UserInterest)
        if user_id:
            stmt = stmt.where(UserInterest.user_id == user_id)
        elif anonymous_id:
            stmt = stmt.where(UserInterest.anonymous_id == anonymous_id)
        else:
            return []
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def _get_read_history(self, session: AsyncSession, user_id: int | None, anonymous_id: str | None) -> set[int]:
        stmt = select(ReadingSession.article_id).where(ReadingSession.is_completed == True)
        if user_id:
            stmt = stmt.where(ReadingSession.user_id == user_id)
        elif anonymous_id:
            stmt = stmt.where(ReadingSession.anonymous_id == anonymous_id)
        else:
            return set()
        res = await session.execute(stmt)
        return set(res.scalars().all())

    async def _retrieve_candidates(self, session: AsyncSession, interests: list[UserInterest], read_ids: set[int]) -> list[Candidate]:
        if not interests: return []
        categories = [i.entity_id for i in interests if i.entity_type == "CATEGORY"]

        # We fetch recent articles overlapping categories for now
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=14)

        stmt = select(ProcessedArticle).where(
            ProcessedArticle.published_status == "published",
            ProcessedArticle.is_test_data == False,
            ProcessedArticle.published_at >= cutoff
        ).order_by(desc(ProcessedArticle.published_at)).limit(100)

        # Simple heuristic: if we have categories, filter by them
        if categories:
            from app.models.category import Category
            cat_stmt = select(Category.id).where(Category.name.in_(categories))
            cat_res = await session.execute(cat_stmt)
            cat_ids = cat_res.scalars().all()
            if cat_ids:
                stmt = stmt.where(ProcessedArticle.category_id.in_(cat_ids))

        res = await session.execute(stmt)
        articles = res.scalars().all()
        return [Candidate(a) for a in articles]

    async def _expand_candidates(self, session: AsyncSession, candidates: list[Candidate], read_ids: set[int]) -> list[Candidate]:
        # Inject Trending or latest
        existing_ids = {c.article.id for c in candidates}
        stmt = select(ProcessedArticle).where(
            ProcessedArticle.published_status == "published",
            ProcessedArticle.is_test_data == False,
            ProcessedArticle.id.notin_(existing_ids)
        ).order_by(desc(ProcessedArticle.published_at)).limit(20)
        res = await session.execute(stmt)
        for a in res.scalars().all():
            candidates.append(Candidate(a))
        return candidates

    def _filter_eligibility(self, candidates: list[Candidate], read_ids: set[int]) -> list[Candidate]:
        return [c for c in candidates if c.article.id not in read_ids]

    def _score_candidates(self, candidates: list[Candidate], interests: list[UserInterest]):
        for c in candidates:
            # Similarity against interests
            sim = 0.0
            best_interest = None
            max_conf = 0.0
            for i in interests:
                if i.entity_type == "CATEGORY":
                    # naive matching by checking if article has category name (needs relation or string match)
                    # We will assign a baseline similarity if it's recent
                    sim += i.affinity * 0.1
                    if i.confidence > max_conf:
                        max_conf = i.confidence
                        best_interest = i
            c.similarity_score = min(sim, 1.0)
            c.confidence = max_conf
            c.dominant_interest = best_interest
            c.calculate_final()

    def _apply_freshness(self, candidates: list[Candidate]):
        now = datetime.now(timezone.utc)
        for c in candidates:
            if c.article.published_at:
                age_hours = (now - c.article.published_at).total_seconds() / 3600
                decay = math.exp(-0.02 * age_hours)
                c.freshness_score = decay
            c.calculate_final()

    def _apply_diversity(self, candidates: list[Candidate]):
        candidates.sort(key=lambda c: c.final_score, reverse=True)
        seen_topics = set()
        seen_sources = set()

        for c in candidates:
            penalty = 0.0
            # Source diversity
            src = c.article.source_name
            if src in seen_sources:
                penalty += 0.2
            else:
                seen_sources.add(src)

            # Topic diversity (naively using category_id for now as proxy)
            cat = c.article.category_id
            if cat in seen_topics:
                penalty += 0.3
            else:
                seen_topics.add(cat)

            c.diversity_penalty = min(penalty, 1.0)
            c.calculate_final()

    def _explain(self, c: Candidate) -> RecommendationResponse:
        reason_msg = "Recommended based on your reading history."
        if c.dominant_interest:
            if c.dominant_interest.entity_type == "CATEGORY":
                reason_msg = f"Because you frequently read about {c.dominant_interest.entity_id}."
            elif c.dominant_interest.entity_type == "TOPIC":
                reason_msg = f"From a topic you've recently explored: {c.dominant_interest.entity_id}."

        reason = RecommendationReason(
            type="INTEREST_MATCH" if c.dominant_interest else "TRENDING",
            message=reason_msg
        )

        article_dict = {
            "id": c.article.id,
            "title": c.article.title,
            "slug": c.article.slug,
            "summary": c.article.summary,
            "hero_image": c.article.hero_image or c.article.image_url,
            "source_name": c.article.source_name,
            "published_at": c.article.published_at.isoformat() if c.article.published_at else None,
        }

        return RecommendationResponse(
            article=article_dict,
            score=round(c.final_score, 4),
            confidence=round(c.confidence, 4),
            reason=reason,
            strategy="behavioral_feed"
        )

class TrendingStrategy(RecommendationStrategy):
    async def recommend(self, session: AsyncSession, user_id: int | None, anonymous_id: str | None, limit: int) -> list[RecommendationResponse]:
        stmt = select(ProcessedArticle).where(
            ProcessedArticle.published_status == "published",
            ProcessedArticle.is_test_data == False
        ).order_by(desc(ProcessedArticle.published_at)).limit(limit)

        res = await session.execute(stmt)
        articles = res.scalars().all()

        results = []
        for a in articles:
            article_dict = {
                "id": a.id,
                "title": a.title,
                "slug": a.slug,
                "summary": a.summary,
                "hero_image": a.hero_image or a.image_url,
                "source_name": a.source_name,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            results.append(RecommendationResponse(
                article=article_dict,
                score=0.8,
                confidence=1.0,
                reason=RecommendationReason(type="TRENDING", message="Trending among readers right now."),
                strategy="trending_feed"
            ))
        return results

class RecommendationEngine:
    async def get_feed(self, session: AsyncSession, user_id: int | None, anonymous_id: str | None, limit: int = 10) -> list[RecommendationResponse]:
        from app.services.recommendations.registry import RecommendationRegistry
        behavioral = RecommendationRegistry.get("behavioral")
        results = await behavioral.recommend(session, user_id, anonymous_id, limit)

        # Cold start fallback
        if len(results) < min(3, limit):
            trending = RecommendationRegistry.get("trending")
            fallback = await trending.recommend(session, user_id, anonymous_id, limit - len(results))
            results.extend(fallback)

        return results[:limit]
