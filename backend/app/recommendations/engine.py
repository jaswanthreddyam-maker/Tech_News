from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import RecommendationProfile, UserAffinityProfile
from app.recommendations.capability import RecommendationCapability, RecommendationCost, recommendation_registry
from app.recommendations.schemas import RecommendationCandidate, RecommendationExplanation, RecommendationRequest


class TrendingCapability(RecommendationCapability):
    priority = 50
    cost = RecommendationCost.LOW
    version = "1.0"

    @property
    def strategy_name(self) -> str:
        return "TRENDING"

    def supports(self, request: RecommendationRequest) -> bool:
        return True

    async def retrieve_candidates(self, request: RecommendationRequest, session: AsyncSession) -> list[RecommendationCandidate]:
        stmt = select(RecommendationProfile).limit(100) # Pre-fetch pool
        profiles = (await session.execute(stmt)).scalars().all()

        candidates = []
        for p in profiles:
            feats = p.ranking_features or {}
            ctx_feats = p.context_features or {}
            candidates.append(RecommendationCandidate(
                article_id=p.article_id,
                score=0.0, # Will be set in score()
                strategy=self.strategy_name,
                features=ctx_feats,
                metadata={"ranking_features": feats}
            ))
        return candidates

    def score(self, candidates: list[RecommendationCandidate], request: RecommendationRequest) -> list[RecommendationCandidate]:
        for c in candidates:
            feats = c.metadata.get("ranking_features", {})
            c.score = (
                feats.get("behavior", 0.0) +
                feats.get("editorial", 1.0) +
                feats.get("engagement", 0.0) +
                feats.get("freshness", 1.0)
            )
        return candidates

    def explain(self, candidate: RecommendationCandidate, request: RecommendationRequest) -> RecommendationExplanation:
        return RecommendationExplanation(
            reason="TRENDING",
            weight=1.0,
            confidence=0.9,
            metadata={"source": "trending_algorithm"}
        )

class RelatedCapability(RecommendationCapability):
    priority = 20
    cost = RecommendationCost.MEDIUM
    version = "1.0"

    @property
    def strategy_name(self) -> str:
        return "RELATED"

    def supports(self, request: RecommendationRequest) -> bool:
        return bool(request.context.article_id)

    async def retrieve_candidates(self, request: RecommendationRequest, session: AsyncSession) -> list[RecommendationCandidate]:
        source_id = request.context.article_id
        stmt = select(RecommendationProfile).where(RecommendationProfile.article_id == source_id)
        source_profile = (await session.execute(stmt)).scalar_one_or_none()

        if not source_profile or not source_profile.context_features.get("primary_topic"):
            return []

        topic = source_profile.context_features.get("primary_topic")
        stmt = select(RecommendationProfile).where(RecommendationProfile.article_id != source_id).limit(50)
        all_profiles = (await session.execute(stmt)).scalars().all()

        candidates = []
        for p in all_profiles:
            ctx_feats = p.context_features or {}
            if ctx_feats.get("primary_topic") == topic:
                feats = p.ranking_features or {}
                candidates.append(RecommendationCandidate(
                    article_id=p.article_id,
                    score=0.0,
                    strategy=self.strategy_name,
                    features=ctx_feats,
                    metadata={"ranking_features": feats}
                ))
        return candidates

    def score(self, candidates: list[RecommendationCandidate], request: RecommendationRequest) -> list[RecommendationCandidate]:
        for c in candidates:
            feats = c.metadata.get("ranking_features", {})
            c.score = feats.get("freshness", 1.0)
        return candidates

    def explain(self, candidate: RecommendationCandidate, request: RecommendationRequest) -> RecommendationExplanation:
        return RecommendationExplanation(
            reason="RELATED",
            weight=0.8,
            confidence=0.85,
            metadata={"topic": candidate.features.get("primary_topic")}
        )

class ForYouCapability(RecommendationCapability):
    priority = 80
    cost = RecommendationCost.MEDIUM
    version = "1.0"

    @property
    def strategy_name(self) -> str:
        return "FOR_YOU"

    def supports(self, request: RecommendationRequest) -> bool:
        return bool(request.context.user_id)

    async def retrieve_candidates(self, request: RecommendationRequest, session: AsyncSession) -> list[RecommendationCandidate]:
        user_id = request.context.user_id
        stmt = select(UserAffinityProfile).where(UserAffinityProfile.user_id == user_id).order_by(desc(UserAffinityProfile.weight)).limit(5)
        affinities = (await session.execute(stmt)).scalars().all()

        if not affinities:
            return []

        topics = [a.subject_id for a in affinities if a.subject_type.name == "TOPIC"]
        if not topics:
            return []

        stmt = select(RecommendationProfile).limit(100)
        profiles = (await session.execute(stmt)).scalars().all()

        candidates = []
        for p in profiles:
            ctx_feats = p.context_features or {}
            p_topic = ctx_feats.get("primary_topic")
            if p_topic in topics:
                feats = p.ranking_features or {}
                candidates.append(RecommendationCandidate(
                    article_id=p.article_id,
                    score=0.0,
                    strategy=self.strategy_name,
                    features=ctx_feats,
                    metadata={"ranking_features": feats}
                ))
        return candidates

    def score(self, candidates: list[RecommendationCandidate], request: RecommendationRequest) -> list[RecommendationCandidate]:
        for c in candidates:
            feats = c.metadata.get("ranking_features", {})
            c.score = feats.get("engagement", 0.0) + feats.get("freshness", 1.0)
        return candidates

    def explain(self, candidate: RecommendationCandidate, request: RecommendationRequest) -> RecommendationExplanation:
        return RecommendationExplanation(
            reason="FOLLOWED_TOPIC",
            weight=0.9,
            confidence=0.95,
            metadata={"topic": candidate.features.get("primary_topic")}
        )

recommendation_registry.register(TrendingCapability())
recommendation_registry.register(RelatedCapability())
recommendation_registry.register(ForYouCapability())
