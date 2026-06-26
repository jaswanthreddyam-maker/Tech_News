import logging
from typing import Any

from app.ai.chat.context_builder import ContextBuilder

logger = logging.getLogger("tech_news.ai.chat.digest_context_builder")


class DigestContextBuilder(ContextBuilder):
    """
    Constructs the prompt for a Daily Digest, separating INTERNAL WORKSPACE CHANGES
    from EXTERNAL NEWS RELEVANT TO WORKSPACE.
    """

    def build_context(self, system_prompt: str, retrieved_items: list[dict[str, Any]]) -> str:
        internal_notes = [item for item in retrieved_items if item.get("type") == "internal_note"]
        internal_arts = [item for item in retrieved_items if item.get("type") == "internal_article"]
        activities = [item for item in retrieved_items if item.get("type") == "internal_activity"]
        external_arts = [item for item in retrieved_items if item.get("type") == "external_article"]

        context_parts = [system_prompt, "\n\n--- INTERNAL WORKSPACE CHANGES ---\n"]
        current_tokens = self.count_tokens("".join(context_parts))

        if activities:
            act_text = f"\n## WORKSPACE ACTIVITY LOG\n{activities[0]['content']}\n"
            context_parts.append(act_text)
            current_tokens += self.count_tokens(act_text)

        if internal_notes:
            context_parts.append("\n## RECENTLY EDITED NOTES\n")
            for note in internal_notes:
                note_text = f'\n<note id="{note["id"]}">\nTitle: {note["title"]}\nContent: {note["content"]}\n</note>\n'
                note_tokens = self.count_tokens(note_text)
                if current_tokens + note_tokens > (self.max_tokens - 4000):
                    break
                context_parts.append(note_text)
                current_tokens += note_tokens

        if internal_arts:
            context_parts.append("\n## RECENTLY PINNED ARTICLES\n")
            for article in internal_arts:
                art_text = f'\n<article id="{article["id"]}">\nTitle: {article["title"]}\nContent: {article["content"]}\n</article>\n'
                art_tokens = self.count_tokens(art_text)
                if current_tokens + art_tokens > (self.max_tokens - 3000):
                    break
                context_parts.append(art_text)
                current_tokens += art_tokens

        context_parts.append("\n\n--- EXTERNAL NEWS RELEVANT TO WORKSPACE ---\n")

        if external_arts:
            context_parts.append(
                "\n## NEW PUBLISHED ARTICLES\nThese articles match the user's workspace topics but have NOT been pinned yet.\n"
            )
            for article in external_arts:
                art_text = f'\n<article id="{article["id"]}">\nTitle: {article["title"]}\nContent: {article["content"]}\n</article>\n'
                art_tokens = self.count_tokens(art_text)
                if current_tokens + art_tokens > (self.max_tokens - 1000):
                    break
                context_parts.append(art_text)
                current_tokens += art_tokens

        context_parts.append("\n--- END CONTEXT ---\n")
        return "".join(context_parts)
