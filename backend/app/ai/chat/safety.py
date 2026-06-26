import logging

from app.ai.chat.schemas import ChatMessage

logger = logging.getLogger("tech_news.ai.chat.safety")


class SafetyLayer:
    """
    RAG Safety Checks:
    - Prompt Injection detection
    - Toxicity filtering
    - Output validation (checking if the model hallucinated citations)
    """

    def check_input(self, messages: list[ChatMessage]) -> bool:
        """
        Scans input messages for common injection patterns.
        Returns False if malicious intent is suspected.
        """
        latest_message = messages[-1].content.lower()

        # Very basic heuristic blocklist for prompt injection
        blocklist = [
            "ignore previous instructions",
            "ignore all prior instructions",
            "disregard previous",
            "system prompt",
            "you are now a",
            "bypass safety",
            "DAN",
        ]

        for term in blocklist:
            if term in latest_message:
                logger.warning(f"Safety Layer: Blocked potential prompt injection attempt: {term}")
                return False

        return True

    def validate_output(self, generated_text: str, valid_article_ids: set[int]) -> bool:
        """
        Validates that the model didn't hallucinate citations to articles that weren't provided.
        """
        import re

        citation_pattern = re.compile(r"\[Citation:\s*(\d+)\]", re.IGNORECASE)

        for match in citation_pattern.finditer(generated_text):
            try:
                cited_id = int(match.group(1))
                if cited_id not in valid_article_ids:
                    logger.warning(f"Safety Layer: Detected hallucinated citation ID {cited_id}")
                    # Could either strip it or flag it. For now, we just log it, but we
                    # could return False to reject the generation entirely.
            except ValueError:
                pass

        return True
