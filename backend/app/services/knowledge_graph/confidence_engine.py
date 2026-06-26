import logging
import math
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

class BaseScorer:
    def score(self, context: dict[str, Any]) -> float:
        raise NotImplementedError()

class EvidenceScore(BaseScorer):
    def score(self, context: dict[str, Any]) -> float:
        evidence_count = context.get("evidence_count", 0)
        # Cap at 5 pieces of evidence yielding a score of 1.0
        return min(1.0, evidence_count / 5.0)

class SourceCredibilityScore(BaseScorer):
    def score(self, context: dict[str, Any]) -> float:
        return context.get("source_credibility", 0.5)

class AgreementScore(BaseScorer):
    def score(self, context: dict[str, Any]) -> float:
        # High score if no conflicts, lower if conflicting observations exist
        conflicts = context.get("conflict_count", 0)
        return max(0.0, 1.0 - (conflicts * 0.2))

class RecencyScore(BaseScorer):
    def score(self, context: dict[str, Any]) -> float:
        return 1.0 # Base recency, exponential decay handled separately

class ConsistencyScore(BaseScorer):
    def score(self, context: dict[str, Any]) -> float:
        return context.get("consistency_rating", 1.0)

class ConfidenceEngine:
    """
    Computes dynamic confidence scores using modular sub-scorers and applies exponential decay.
    """
    def __init__(self):
        self.scorers: list[BaseScorer] = [
            EvidenceScore(),
            SourceCredibilityScore(),
            AgreementScore(),
            RecencyScore(),
            ConsistencyScore()
        ]

    def calculate_base_confidence(self, context: dict[str, Any]) -> float:
        if not self.scorers:
            return 0.5

        total = sum(scorer.score(context) for scorer in self.scorers)
        return total / len(self.scorers)

    def apply_decay(self, base_confidence: float, last_updated: datetime, decay_lambda: float = 0.001) -> float:
        """
        Applies exponential decay formula: confidence = base * e^(-lambda * t)
        where t is days since last_updated.
        """
        now = datetime.now(timezone.utc)
        delta_days = (now - last_updated).days
        if delta_days < 0:
            delta_days = 0

        decayed = base_confidence * math.exp(-decay_lambda * delta_days)
        return max(0.0, min(1.0, decayed))
