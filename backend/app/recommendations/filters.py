from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventEnvelope
from app.recommendations.schemas import RecommendationCandidate, RecommendationRequest


class RecommendationFilter(ABC):
    priority: int = 10

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def supports(self, request: RecommendationRequest) -> bool:
        return True

    @abstractmethod
    async def apply(self, candidate: RecommendationCandidate, request: RecommendationRequest, session: AsyncSession) -> bool:
        """Return True if candidate passes filter, False to drop"""
        pass

class AlreadyReadFilter(RecommendationFilter):
    priority = 10

    @property
    def name(self) -> str:
        return "ALREADY_READ"

    def supports(self, request: RecommendationRequest) -> bool:
        return bool(request.context.user_id)

    async def apply(self, candidate: RecommendationCandidate, request: RecommendationRequest, session: AsyncSession) -> bool:
        if not request.context.user_id:
            return True
        stmt = select(EventEnvelope).where(
            EventEnvelope.provider == request.context.user_id,
            EventEnvelope.event_type == "ARTICLE_COMPLETED",
            EventEnvelope.subject_id == candidate.article_id
        ).limit(1)
        result = (await session.execute(stmt)).scalar_one_or_none()
        return result is None

class LanguageFilter(RecommendationFilter):
    priority = 20

    @property
    def name(self) -> str:
        return "LANGUAGE"

    def supports(self, request: RecommendationRequest) -> bool:
        return bool(request.context.language)

    async def apply(self, candidate: RecommendationCandidate, request: RecommendationRequest, session: AsyncSession) -> bool:
        if not request.context.language:
            return True
        candidate_lang = candidate.features.get("language")
        if not candidate_lang:
            return True
        return candidate_lang == request.context.language

class HiddenArticleFilter(RecommendationFilter):
    priority = 100

    @property
    def name(self) -> str:
        return "HIDDEN"

    async def apply(self, candidate: RecommendationCandidate, request: RecommendationRequest, session: AsyncSession) -> bool:
        is_hidden = candidate.features.get("is_hidden", False)
        return not is_hidden

FILTER_REGISTRY: dict[str, RecommendationFilter] = {}

def register_filter(filter_cls: RecommendationFilter):
    FILTER_REGISTRY[filter_cls.name] = filter_cls

register_filter(AlreadyReadFilter())
register_filter(LanguageFilter())
register_filter(HiddenArticleFilter())

def get_filters(names: list[str]) -> list[RecommendationFilter]:
    # Return filters sorted by priority descending
    filters = [FILTER_REGISTRY[n] for n in names if n in FILTER_REGISTRY]
    return sorted(filters, key=lambda f: f.priority, reverse=True)
