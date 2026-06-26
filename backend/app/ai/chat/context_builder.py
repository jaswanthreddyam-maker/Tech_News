import logging
from typing import Any

import tiktoken

logger = logging.getLogger("tech_news.ai.chat.context_builder")


class ContextBuilder:
    """
    Constructs the final prompt context, ensuring it fits within the model's token limits.
    """

    def __init__(self, model_name: str = "gpt-4o-mini", max_tokens: int = 100000):
        self.model_name = model_name
        self.max_tokens = max_tokens
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def build_context(self, system_prompt: str, retrieved_articles: list[dict[str, Any]]) -> str:
        """
        Assembles the knowledge objects into structured semantic sections for the LLM.
        """
        articles = [item for item in retrieved_articles if item.get("type", "article") == "article"]
        entities = [item for item in retrieved_articles if item.get("type") == "entity"]
        topics = [item for item in retrieved_articles if item.get("type") == "topic"]
        timeline_events = [item for item in retrieved_articles if item.get("type") == "timeline_event"]
        relationships = [item for item in retrieved_articles if item.get("type") == "relationship"]

        context_parts = [system_prompt, "\n\n--- KNOWLEDGE CONTEXT ---\n"]
        current_tokens = self.count_tokens("".join(context_parts))

        if articles:
            context_parts.append("\n[ARTICLE_CONTENT]\n")
            for article in articles:
                art_text = f'<article id="{article.get("id")}">\nTitle: {article.get("title")}\nContent: {article.get("content")}\n</article>\n'
                art_tokens = self.count_tokens(art_text)
                if current_tokens + art_tokens > (self.max_tokens - 2000):
                    break
                context_parts.append(art_text)
                current_tokens += art_tokens

        if entities:
            context_parts.append("\n[ENTITIES]\n")
            for ent in entities:
                ent_text = f'<entity id="{ent.get("id")}">\nName: {ent.get("title")}\nDescription: {ent.get("description")}\n</entity>\n'
                ent_tokens = self.count_tokens(ent_text)
                if current_tokens + ent_tokens > (self.max_tokens - 2000):
                    break
                context_parts.append(ent_text)
                current_tokens += ent_tokens

        if topics:
            context_parts.append("\n[TOPICS]\n")
            for top in topics:
                top_text = f'<topic id="{top.get("id")}">\nName: {top.get("title")}\nDetails: {top.get("description")}\n</topic>\n'
                top_tokens = self.count_tokens(top_text)
                if current_tokens + top_tokens > (self.max_tokens - 2000):
                    break
                context_parts.append(top_text)
                current_tokens += top_tokens

        if timeline_events:
            context_parts.append("\n[TIMELINE]\n")
            for evt in timeline_events:
                evt_text = f'<event id="{evt.get("id")}">\n{evt.get("title")}: {evt.get("description")}\n</event>\n'
                evt_tokens = self.count_tokens(evt_text)
                if current_tokens + evt_tokens > (self.max_tokens - 2000):
                    break
                context_parts.append(evt_text)
                current_tokens += evt_tokens

        if relationships:
            context_parts.append("\n[RELATIONSHIPS]\n")
            for rel in relationships:
                rel_text = f'<relationship id="{rel.get("id")}">\n{rel.get("title")}\n</relationship>\n'
                rel_tokens = self.count_tokens(rel_text)
                if current_tokens + rel_tokens > (self.max_tokens - 2000):
                    break
                context_parts.append(rel_text)
                current_tokens += rel_tokens

        context_parts.append("\n--- END KNOWLEDGE CONTEXT ---\n")
        context_parts.append(
            "INSTRUCTIONS: Base your answer ON THE KNOWLEDGE CONTEXT provided above. When you reference information, you MUST cite it using the format [Citation: ID], for example [Citation: 12] or [Citation: apple_inc]. Do not hallucinate outside knowledge."
        )

        return "".join(context_parts)


class WorkspaceContextBuilder(ContextBuilder):
    """
    Constructs the prompt for a Workspace, distinguishing between Pinned Articles and User Notes.
    """

    def build_context(self, system_prompt: str, retrieved_items: list[dict[str, Any]]) -> str:
        articles = [item for item in retrieved_items if item.get("type") == "article"]
        notes = [item for item in retrieved_items if item.get("type") == "note"]

        context_parts = [system_prompt, "\n\n--- RESEARCH WORKSPACE ---\n"]
        current_tokens = self.count_tokens("".join(context_parts))

        # Add User Notes First (High priority)
        if notes:
            context_parts.append(
                "\n## USER NOTES\nThese are personal notes written by the user. Treat them as highly important context.\n"
            )
            for note in notes:
                note_text = f'\n<note id="{note["id"]}">\nTitle: {note["title"]}\nContent: {note["content"]}\n</note>\n'
                note_tokens = self.count_tokens(note_text)
                if current_tokens + note_tokens > (self.max_tokens - 3000):
                    break
                context_parts.append(note_text)
                current_tokens += note_tokens

        # Add Pinned Articles
        if articles:
            context_parts.append("\n## PINNED ARTICLES\nThese are source documents saved in the workspace.\n")
            for article in articles:
                art_text = f'\n<article id="{article["id"]}">\nTitle: {article["title"]}\nContent: {article["content"]}\n</article>\n'
                art_tokens = self.count_tokens(art_text)
                if current_tokens + art_tokens > (self.max_tokens - 2000):
                    break
                context_parts.append(art_text)
                current_tokens += art_tokens

        context_parts.append("\n--- END WORKSPACE ---\n")
        context_parts.append(
            "INSTRUCTIONS: Base your answer on the Workspace context provided above. Prioritize integrating the User Notes with the Pinned Articles. When you reference an article or note, cite it using [Citation: ID]. Do not hallucinate outside knowledge."
        )

        return "".join(context_parts)
