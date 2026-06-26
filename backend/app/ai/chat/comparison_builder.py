from typing import Any

from app.ai.chat.context_builder import ContextBuilder


class ComparisonContextBuilder(ContextBuilder):
    """
    Builds context specifically structured for comparisons.
    Groups retrieved articles cleanly.
    """

    def build_context(self, system_instructions: str, retrieved_articles: list[dict[str, Any]]) -> str:
        """
        Builds the structured system prompt with the provided context.
        """
        if not retrieved_articles:
            context_str = "No relevant articles found for the given contexts."
        else:
            # For now, we present the deduplicated pool of articles.
            # If we wanted to, we could tag them if they came from Context A vs Context B,
            # but since they are interleaved and deduplicated, presenting them clearly
            # as a consolidated pool of evidence works perfectly for the LLM to compare.
            context_blocks = []
            for art in retrieved_articles:
                block = f"--- ARTICLE ID: {art['id']} ---\nTITLE: {art['title']}\nCONTENT:\n{art['content']}\n"
                context_blocks.append(block)

            context_str = "\n".join(context_blocks)

        prompt = f"""{system_instructions}

        ### RETRIEVED EVIDENCE
        {context_str}
        """

        # Truncate if it exceeds maximum context window
        if self.count_tokens(prompt) > self.max_tokens:
            prompt = self._truncate_context(prompt)

        return prompt
