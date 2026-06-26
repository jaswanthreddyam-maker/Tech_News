import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class ResearchIntent(str, Enum):
    TIMELINE_QUERY = "TIMELINE_QUERY"
    ENTITY_COMPARISON = "ENTITY_COMPARISON"
    TOPIC_EVOLUTION = "TOPIC_EVOLUTION"
    EVIDENCE_SEARCH = "EVIDENCE_SEARCH"
    UNKNOWN = "UNKNOWN"

class IntentDetector:
    """
    Analyzes an incoming question to classify its research intent and extract key parameters.
    """
    def __init__(self):
        pass

    def detect(self, question: str) -> dict[str, Any]:
        """
        In production, this would use an LLM or specialized classifier.
        For now, rule-based prototyping.
        """
        lower_q = question.lower()
        intent = ResearchIntent.UNKNOWN
        entities = []

        if "compare" in lower_q or "difference" in lower_q or "vs" in lower_q:
            intent = ResearchIntent.ENTITY_COMPARISON
        elif "timeline" in lower_q or "history" in lower_q or "when" in lower_q:
            intent = ResearchIntent.TIMELINE_QUERY
        elif "evolution" in lower_q or "how has" in lower_q:
            intent = ResearchIntent.TOPIC_EVOLUTION
        elif "evidence" in lower_q or "proof" in lower_q:
            intent = ResearchIntent.EVIDENCE_SEARCH

        logger.info(f"IntentDetector: Classified '{question}' as {intent.value}")

        return {
            "intent": intent.value,
            "entities": entities,
            "raw_question": question
        }
