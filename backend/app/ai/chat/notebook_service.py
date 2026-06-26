import logging
import os
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat.context_builder import WorkspaceContextBuilder
from app.ai.chat.retrieval_strategy import RetrievalStrategyFactory
from app.ai.chat.schemas import ConversationMode, StreamEventType
from app.ai.chat.stream_service import StreamService
from app.core.config import settings
from app.models.workspace import NotebookOperation, NoteChangeType
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger("tech_news.ai.chat.notebook_service")


class NotebookService:
    """
    Dedicated service for transforming user information into knowledge.
    Operates without conversation persistence or conversational semantics.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.workspace_builder = WorkspaceContextBuilder(model_name=getattr(settings, "CHAT_MODEL", "gpt-4o-mini"))
        api_key = getattr(settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.chat_model = getattr(settings, "CHAT_MODEL", "gpt-4o-mini")
        self.workspace_service = WorkspaceService(db)

    async def stream_operation(
        self,
        workspace_id: int,
        note_id: int,
        operation: NotebookOperation,
        selection: str,
        full_content: str,
        owner_type: str,
        owner_id: str,
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            yield StreamService.format_error("AI Provider is not configured.")
            return

        # Fetch Workspace Context
        retrieval_strategy = RetrievalStrategyFactory.get_strategy(ConversationMode.WORKSPACE)

        # We use the selection or full_content as the query for semantic search
        query = selection if selection.strip() else full_content
        retrieved_articles = await retrieval_strategy.retrieve(query=query, db=self.db, workspace_id=workspace_id)

        # Build Context
        system_instructions = self._get_prompt_for_operation(operation)
        system_context = self.workspace_builder.build_context(system_instructions, retrieved_articles)

        llm_messages = [{"role": "system", "content": system_context}]

        # Add the content
        user_prompt = f"Full Document:\n\n{full_content}\n\n"
        if selection:
            user_prompt += f"Selected Text to {operation.value}:\n\n{selection}\n"
        else:
            user_prompt += f"Please {operation.value} the entire document.\n"

        llm_messages.append({"role": "user", "content": user_prompt})

        generated_text = ""
        try:
            stream = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=llm_messages,
                stream=True,
                temperature=0.4,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    generated_text += text_chunk
                    yield StreamService.format_sse(StreamEventType.TOKEN, {"text": text_chunk})

        except Exception as e:
            logger.error(f"Notebook Service Error: {e}")
            yield StreamService.format_error("Generation failed due to provider error.")
            return

        yield StreamService.format_sse(StreamEventType.COMPLETED, {})

        # We do NOT auto-save the result into the database here for EXPAND/REFINE/REWRITE
        # The frontend editor receives the text and the user can decide to save it manually
        # OR we could save it. Since it's streaming into the editor, the editor state will hold the change.
        # But for SUMMARIZE, we probably want to update the DB directly, or let the frontend do it.
        # We will let the frontend call an update endpoint when they are happy, or we can auto-save.
        # Given it streams to the editor, the user should explicitly save or auto-save triggers later.

    async def summarize_note(self, workspace_id: int, note_id: int, owner_type: str, owner_id: str) -> str | None:
        """Non-streaming operation specifically to generate a summary for a note."""
        if not self.client:
            return None

        workspace = await self.workspace_service.get_workspace(workspace_id, owner_type, owner_id)
        if not workspace:
            return None

        # Find note
        note = next((n for n in workspace.notes if n.id == note_id), None)
        if not note:
            return None

        retrieval_strategy = RetrievalStrategyFactory.get_strategy(ConversationMode.WORKSPACE)
        retrieved_articles = await retrieval_strategy.retrieve(
            query=note.content, db=self.db, workspace_id=workspace_id
        )
        system_context = self.workspace_builder.build_context(
            "You are an AI Research Assistant. Generate a concise 1-2 sentence summary of this note.",
            retrieved_articles,
        )

        try:
            resp = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "system", "content": system_context}, {"role": "user", "content": note.content}],
                max_tokens=100,
                temperature=0.3,
            )
            summary = resp.choices[0].message.content.strip()

            # Save the summary to the note
            await self.workspace_service.update_note(
                workspace_id=workspace_id,
                owner_type=owner_type,
                owner_id=owner_id,
                note_id=note_id,
                content=note.content,
                summary=summary,
                change_type=NoteChangeType.AI_SUMMARIZE,
                created_by="ai",
            )
            return summary
        except Exception as e:
            logger.error(f"Notebook Summarize Error: {e}")
            return None

    def _get_prompt_for_operation(self, operation: NotebookOperation) -> str:
        base = "You are an expert AI Research Assistant helping the user craft their research notebook."
        if operation == NotebookOperation.EXPAND:
            return (
                base
                + " Expand on the user's selected text using the provided workspace context. Add relevant details, facts, and explanations. Output ONLY the expanded markdown text."
            )
        elif operation == NotebookOperation.REFINE:
            return (
                base
                + " Refine the user's selected text for clarity, conciseness, and professional tone. Output ONLY the refined markdown text."
            )
        elif operation == NotebookOperation.REWRITE:
            return base + " Rewrite the user's selected text completely. Output ONLY the rewritten markdown text."
        elif operation == NotebookOperation.OUTLINE:
            return (
                base
                + " Create a structured markdown outline based on the user's document and the workspace context. Output ONLY the markdown outline."
            )
        elif operation == NotebookOperation.FIND_CITATIONS:
            return (
                base
                + " Analyze the user's selected text and insert markdown inline citations (e.g., [1]) linking to the relevant provided workspace articles. Output ONLY the updated text with citations."
            )
        return base + " Perform the requested operation. Output ONLY the resulting markdown."
