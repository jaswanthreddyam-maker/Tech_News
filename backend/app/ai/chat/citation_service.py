import logging
import re
from typing import Any

from app.ai.chat.schemas import Citation

logger = logging.getLogger("tech_news.ai.chat.citation_service")


class CitationService:
    """
    Parses LLM output for citation markers like [Citation: 123] and builds structured JSON metadata.
    """

    CITATION_PATTERN = re.compile(r"\[Citation:\s*(\d+)\]", re.IGNORECASE)

    def extract_citations(self, text: str, retrieved_articles: list[dict[str, Any]]) -> tuple[str, list[Citation]]:
        """
        Extracts citations from the text, maps them to the retrieved articles,
        and returns the cleaned text (with simple [1] style markers) and the structured list of Citations.
        """
        found_ids = set()

        # Find all cited IDs
        for match in self.CITATION_PATTERN.finditer(text):
            try:
                found_ids.add(int(match.group(1)))
            except ValueError:
                pass

        # Build structured citations
        structured_citations = []
        id_to_index = {}
        current_index = 1

        for art in retrieved_articles:
            art_id = art.get("id")
            if art_id in found_ids:
                citation = Citation(
                    article_id=art_id, title=art.get("title", ""), url=art.get("url"), score=art.get("score", 0.0)
                )
                structured_citations.append(citation)
                id_to_index[art_id] = current_index
                current_index += 1

        # Replace [Citation: 123] with [1] based on the structured index
        def replacer(match) -> str:
            try:
                art_id = int(match.group(1))
                if art_id in id_to_index:
                    return f"[{id_to_index[art_id]}]"
            except ValueError:
                pass
            return ""  # Remove invalid citations

        cleaned_text = self.CITATION_PATTERN.sub(replacer, text)

        return cleaned_text, structured_citations
