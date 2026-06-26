from typing import ClassVar

from app.services.recommendations.engine import BehavioralStrategy, RecommendationStrategy, TrendingStrategy


class RecommendationRegistry:
    _strategies: ClassVar[dict[str, RecommendationStrategy]] = {}

    @classmethod
    def register(cls, name: str, strategy: RecommendationStrategy):
        cls._strategies[name] = strategy

    @classmethod
    def get(cls, name: str) -> RecommendationStrategy:
        strategy = cls._strategies.get(name)
        if not strategy:
            raise ValueError(f"Strategy {name} not registered in RecommendationRegistry")
        return strategy

# Auto-register core strategies
RecommendationRegistry.register("behavioral", BehavioralStrategy())
RecommendationRegistry.register("trending", TrendingStrategy())
