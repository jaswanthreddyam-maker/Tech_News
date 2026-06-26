import json
from abc import ABC, abstractmethod

from app.schemas.ai_context import AIContext, ContextProfile


class TokenEstimator(ABC):
    @abstractmethod
    def estimate(self, text: str) -> int:
        pass


class CharacterHeuristicTokenEstimator(TokenEstimator):
    def estimate(self, text: str) -> int:
        return len(text) // 4 if text else 0


class ContextBudgetAllocator:
    """
    Ensures that the assembled AIContext fits within a specified token budget.
    We use a rough heuristic: 1 token ≈ 4 characters.
    """

    def __init__(self, estimator: TokenEstimator = None, total_tokens: int = 4000):
        self.estimator = estimator or CharacterHeuristicTokenEstimator()
        self.total_tokens = total_tokens

    def _get_budget(self, profile: ContextProfile) -> dict[str, float]:
        if profile == ContextProfile.SUMMARY:
            return {"primary": 0.90, "related": 0.05, "kg": 0.0, "behavior": 0.0}
        elif profile == ContextProfile.CHAT:
            return {"primary": 0.50, "related": 0.20, "kg": 0.10, "behavior": 0.10}
        return {"primary": 0.60, "related": 0.20, "kg": 0.10, "behavior": 0.05}

    def allocate(self, context: AIContext) -> AIContext:
        """
        Truncates the fields of AIContext to fit within the budgets.
        Modifies the object in place (or rather, the lists/strings inside it).
        """
        budget_ratios = self._get_budget(context.metadata.context_profile)
        # Using a simple character count equivalent for heuristic allocation limits
        total_chars = self.total_tokens * 4

        primary_budget = int(total_chars * budget_ratios["primary"])
        related_budget = int(total_chars * budget_ratios["related"])
        kg_budget = int(total_chars * budget_ratios["kg"])
        behavior_budget = int(total_chars * budget_ratios["behavior"])

        # Primary Article Truncation
        content_len = len(context.primary_article.content) if context.primary_article.content else 0
        if content_len > primary_budget and primary_budget > 0:
            context.primary_article.content = context.primary_article.content[:primary_budget] + "..."

        while context.related_articles and len(json.dumps([r.model_dump() for r in context.related_articles])) > related_budget:
            context.related_articles.pop()

        while context.knowledge_graph.nodes and len(json.dumps(context.knowledge_graph.model_dump())) > kg_budget:
            context.knowledge_graph.nodes.pop()

        if context.behavior and len(json.dumps(context.behavior.model_dump())) > behavior_budget:
            context.behavior.recent_categories = []
            if len(json.dumps(context.behavior.model_dump())) > behavior_budget:
                context.behavior.top_interests = context.behavior.top_interests[:2]

        raw_json = context.to_prompt_string()
        context.metadata.token_estimate = self.estimator.estimate(raw_json)

        return context
