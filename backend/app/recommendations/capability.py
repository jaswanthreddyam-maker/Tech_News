import enum
import logging
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.recommendations.schemas import RecommendationCandidate, RecommendationExplanation, RecommendationRequest

logger = logging.getLogger(__name__)

class RecommendationCost(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class RecommendationCapability(ABC):
    priority: int = 10
    cost: RecommendationCost = RecommendationCost.LOW
    version: str = "1.0"

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        pass

    @abstractmethod
    def supports(self, request: RecommendationRequest) -> bool:
        pass

    @abstractmethod
    async def retrieve_candidates(self, request: RecommendationRequest, session: AsyncSession) -> list[RecommendationCandidate]:
        pass

    @abstractmethod
    def score(self, candidates: list[RecommendationCandidate], request: RecommendationRequest) -> list[RecommendationCandidate]:
        pass

    def sort(self, candidates: list[RecommendationCandidate], request: RecommendationRequest) -> list[RecommendationCandidate]:
        return sorted(candidates, key=lambda c: c.score, reverse=True)

    @abstractmethod
    def explain(self, candidate: RecommendationCandidate, request: RecommendationRequest) -> RecommendationExplanation:
        pass

    def post_process(self, candidates: list[RecommendationCandidate], request: RecommendationRequest) -> list[RecommendationCandidate]:
        return candidates

class RecommendationRegistry:
    def __init__(self):
        self._capabilities: dict[str, RecommendationCapability] = {}

    def register(self, capability: RecommendationCapability):
        if capability.strategy_name in self._capabilities:
            existing = self._capabilities[capability.strategy_name]
            if capability.priority > existing.priority:
                self._capabilities[capability.strategy_name] = capability
        else:
            self._capabilities[capability.strategy_name] = capability

    def get(self, strategy_name: str) -> RecommendationCapability | None:
        return self._capabilities.get(strategy_name)

recommendation_registry = RecommendationRegistry()
