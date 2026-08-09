import json
import logging
import os
import re
import time
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat.citation_service import CitationService
from app.ai.chat.comparison_builder import ComparisonContextBuilder
from app.ai.chat.context_builder import ContextBuilder, WorkspaceContextBuilder
from app.ai.chat.conversation_registry import ConversationRegistry
from app.ai.chat.evaluation import EvaluationFramework, RAGMetrics
from app.ai.chat.memory import MemoryManager
from app.ai.chat.prompt_registry import ChatPromptRegistry
from app.ai.chat.response_cache import ResponseCache
from app.ai.chat.retrieval_strategy import RetrievalStrategyFactory
from app.ai.chat.safety import SafetyLayer
from app.ai.chat.schemas import ChatMessage, ChatRole, ConversationMode, EvidenceBundle, EvidenceItem, StreamEventType
from app.ai.chat.stream_service import StreamService
from app.core.config import settings

logger = logging.getLogger("tech_news.ai.chat.conversation_service")

# Regex to extract the follow-up JSON block appended by the LLM
FOLLOW_UP_PATTERN = re.compile(
    r"```json\s*\n?\s*(\{[^`]*\"followUps\"[^`]*\})\s*\n?\s*```\s*$",
    re.DOTALL,
)


def _extract_follow_ups(text: str) -> tuple[str, list[str]]:
    """Extracts the follow-up JSON block from the end of the LLM response.
    Returns (cleaned_text, follow_up_list).
    """
    match = FOLLOW_UP_PATTERN.search(text)
    if not match:
        return text, []

    try:
        payload = json.loads(match.group(1))
        follow_ups = payload.get("followUps", [])
        if isinstance(follow_ups, list) and all(isinstance(f, str) for f in follow_ups):
            cleaned = text[: match.start()].rstrip()
            return cleaned, follow_ups[:4]
    except (json.JSONDecodeError, AttributeError):
        pass

    return text, []


class ConversationService:
    """
    Coordinates the Chat Pipeline for Phase 7 AI features.
    Focused purely on RAG orchestration; lifecycle management is
    delegated to ConversationRegistry.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory = MemoryManager()
        self.cache = ResponseCache()
        self.prompt_registry = ChatPromptRegistry()
        self.context_builder = ContextBuilder(model_name="gemini-2.0-flash-lite")
        self.workspace_builder = WorkspaceContextBuilder(model_name="gemini-2.0-flash-lite")
        self.comparison_builder = ComparisonContextBuilder(model_name="gemini-2.0-flash-lite")
        self.citation_service = CitationService()
        self.safety = SafetyLayer()
        self.eval = EvaluationFramework()
        self.registry = ConversationRegistry()

        gemini_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
        if gemini_key and gemini_key not in ("mock-happy-path", ""):
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=gemini_key)
            except Exception:
                self.gemini_client = None
        else:
            self.gemini_client = None

        self.chat_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash-lite")

    # ------------------------------------------------------------------
    # Background title generation
    # ------------------------------------------------------------------
    async def _generate_title(self, conversation_id: str, assistant_text: str) -> str | None:
        """Generates a short title from the first assistant response using Gemini."""
        if not self.gemini_client:
            return None

        try:
            import asyncio
            from google.genai import types as genai_types

            prompt = (
                "Generate a concise title (max 6 words) for a conversation "
                "that produced the following response. Return ONLY the title, "
                "no quotes, no punctuation at the end.\n\n"
                f"Response:\n{assistant_text[:500]}"
            )
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.gemini_client.models.generate_content(
                    model=self.chat_model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=20,
                    ),
                ),
            )
            title = (response.text or "").strip().strip('"').strip(".")
            if title:
                await self.registry.rename(conversation_id, title)
                return title
        except Exception as e:
            logger.warning(f"Title generation failed for {conversation_id}: {e}")

        return None

    def _generate_fallback_response(self, retrieved_articles: list[dict], query: str) -> tuple[str, list[str]]:
        clean_query = query.lower().strip().strip("!").strip(".")
        greetings = {"hi", "hello", "hey", "hi there", "hello there", "good morning", "good afternoon", "good evening", "howdy", "yo"}

        if not retrieved_articles:
            if clean_query in greetings:
                return (
                    "Hello! I'm your AI Tech News assistant. How can I help you explore today's tech news?",
                    ["What are the top trending stories today?", "Tell me about recent AI developments."]
                )
            return (
                "I searched the tech news repository, but couldn't find specific articles directly matching your query.",
                ["What are the top trending stories today?", "Tell me about recent AI developments."]
            )

        main_art = retrieved_articles[0]
        title = main_art.get("title", "Article Summary")

        if clean_query in greetings:
            return (
                f"Hello! I'm your AI assistant for **{title}**.\n\nHow can I help you with this article? Feel free to ask for a summary, key takeaways, or related developments!",
                [
                    "What are the main takeaways from this article?",
                    "Why is this story important?",
                    "Show me related stories."
                ]
            )

        content = main_art.get("content") or main_art.get("summary") or main_art.get("description", "")
        
        # Clean text snippet into bullets
        raw_sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 15]
        key_points = raw_sentences[:3]
        bullets = "\n".join(f"• {p}." for p in key_points) if key_points else f"• {content[:300]}..."

        res_text = (
            f"Here are the key takeaways from **{title}**:\n\n"
            f"{bullets}\n\n"
            f"*(Grounded in Tech News repository article context)*"
        )
        follow_ups = [
            f"What else should I know about this story?",
            "What are the related industry reactions?",
            "Show me similar stories."
        ]
        return res_text, follow_ups

    # ------------------------------------------------------------------
    # Main streaming pipeline
    # ------------------------------------------------------------------
    async def stream_chat(
        self,
        conversation_id: str,
        message: str,
        mode: ConversationMode = ConversationMode.GENERAL,
        article_id: int | None = None,
        workspace_id: int | None = None,
        context_a: dict | None = None,
        context_b: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Executes the RAG pipeline and yields SSE formatted chunks.
        """
        start_time = time.time()

        # 1. Store user message in memory
        user_msg = ChatMessage(role=ChatRole.USER, content=message)
        await self.memory.add_message(conversation_id, user_msg)

        # 2. Safety Check Input
        history, summary = await self.memory.get_context(conversation_id)
        if not self.safety.check_input(history):
            yield StreamService.format_error("Message blocked by safety filters.")
            return

        yield StreamService.format_sse(StreamEventType.RETRIEVAL_STARTED, {})

        # 3. Retrieve Context via Strategy
        retrieval_strategy = RetrievalStrategyFactory.get_strategy(mode)
        retrieved_articles = await retrieval_strategy.retrieve(
            query=message,
            db=self.db,
            article_id=article_id,
            workspace_id=workspace_id,
            context_a=context_a,
            context_b=context_b,
        )
        retrieved_ids = [art["id"] for art in retrieved_articles]

        yield StreamService.format_sse(StreamEventType.RETRIEVAL_FINISHED, {"count": len(retrieved_articles)})

        # Emit Provenance
        provenance_items = []
        provenance_summary = {"articles": 0, "notes": 0, "comparisons": 0, "conversations": 0}

        evidence_items = []
        for item in retrieved_articles:
            t = str(item.get("type", "article"))
            if t + "s" in provenance_summary:
                provenance_summary[t + "s"] += 1
            provenance_items.append({"type": t, "id": item["id"], "title": item.get("title"), "url": item.get("url")})

            # Build EvidenceItem
            evidence_items.append(EvidenceItem(
                id=item["id"],
                type=t,
                title=item.get("title"),
                url=item.get("url"),
                description=item.get("description"),
                score=item.get("score")
            ))

        # Basic confidence heuristic
        confidence = "Low"
        if provenance_summary["articles"] + provenance_summary["notes"] > 5:
            confidence = "High"
        elif provenance_summary["articles"] + provenance_summary["notes"] > 2:
            confidence = "Medium"

        evidence_bundle = EvidenceBundle(items=evidence_items, confidence=confidence)

        yield StreamService.format_sse(
            StreamEventType.PROVENANCE,
            {"summary": provenance_summary, "items": provenance_items, "confidence": confidence},
        )

        yield StreamService.format_sse(
            StreamEventType.EVIDENCE_BUNDLE,
            evidence_bundle.model_dump()
        )

        # Emit Comparison Metadata if applicable
        if mode == ConversationMode.COMPARISON:
            count_a = len([a for a in retrieved_articles]) // 2  # Approximate for display if not explicitly tagged
            count_b = len(retrieved_articles) - count_a
            name_a = context_a.value if context_a else "Context A"
            name_b = context_b.value if context_b else "Context B"

            yield StreamService.format_sse(
                StreamEventType.COMPARISON_METADATA,
                {"context_a": {"name": name_a, "sources": count_a}, "context_b": {"name": name_b, "sources": count_b}},
            )

        # 4. Get System Prompt and build context
        system_instructions, prompt_hash = self.prompt_registry.get_prompt(mode)

        # 5. Check Cache
        cached_response = await self.cache.get(message, retrieved_ids, prompt_hash, self.chat_model, mode.value)
        if cached_response:
            yield StreamService.format_sse(StreamEventType.GENERATION_STARTED, {})
            yield StreamService.format_sse(StreamEventType.TOKEN, {"text": cached_response.get("text", "")})
            if cached_response.get("citations"):
                yield StreamService.format_sse(StreamEventType.CITATION, {"citations": cached_response["citations"]})
            if cached_response.get("follow_ups"):
                yield StreamService.format_sse(
                    StreamEventType.SUGGESTED_FOLLOW_UPS,
                    {"follow_ups": cached_response["follow_ups"]},
                )
            yield StreamService.format_sse(StreamEventType.COMPLETED, {})
            return

        # 6. Build LLM Messages
        if mode == ConversationMode.COMPARISON:
            builder = self.comparison_builder
        elif mode == ConversationMode.WORKSPACE:
            builder = self.workspace_builder
        else:
            builder = self.context_builder

        system_context = builder.build_context(system_instructions, retrieved_articles)
        llm_messages: list[dict[str, str]] = [{"role": "system", "content": system_context}]

        if summary:
            llm_messages.append({"role": "system", "content": f"Previous conversation summary: {summary}"})

        for msg in history[-6:]:
            llm_messages.append({"role": msg.role.value, "content": msg.content})

        yield StreamService.format_sse(StreamEventType.GENERATION_STARTED, {})

        # 7. Stream LLM Response
        generated_text = ""
        follow_ups = []
        use_fallback = False
        prompt_tokens = self.context_builder.count_tokens("".join(m["content"] for m in llm_messages))
        completion_tokens = 0

        if not self.gemini_client:
            use_fallback = True
        else:
            try:
                import asyncio
                from google.genai import types as genai_types

                full_prompt = f"System Instructions:\n{system_context}\n\n"
                if summary:
                    full_prompt += f"Previous Conversation Summary:\n{summary}\n\n"
                full_prompt += "Conversation History:\n"
                for msg in history[-6:]:
                    full_prompt += f"{msg.role.value.capitalize()}: {msg.content}\n"
                full_prompt += f"User: {message}\nAssistant:"

                loop = asyncio.get_event_loop()
                stream_response = await loop.run_in_executor(
                    None,
                    lambda: self.gemini_client.models.generate_content_stream(
                        model=self.chat_model,
                        contents=full_prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=0.7,
                            max_output_tokens=1000,
                        ),
                    ),
                )

                for chunk in stream_response:
                    if chunk.text:
                        text_chunk = chunk.text
                        generated_text += text_chunk
                        yield StreamService.format_sse(StreamEventType.TOKEN, {"text": text_chunk})
                        await asyncio.sleep(0.005)

            except Exception as e:
                logger.warning(f"Gemini LLM provider error ({e}). Using grounded fallback response.")
                use_fallback = True

        if use_fallback and not generated_text:
            import asyncio
            fallback_text, fallback_followups = self._generate_fallback_response(retrieved_articles, message)
            generated_text = fallback_text
            follow_ups = fallback_followups

            # Stream fallback tokens cleanly
            words = fallback_text.split(" ")
            for i, word in enumerate(words):
                chunk_str = word + (" " if i < len(words) - 1 else "")
                yield StreamService.format_sse(StreamEventType.TOKEN, {"text": chunk_str})
                await asyncio.sleep(0.015)

        # 8. Extract follow-ups from the single LLM response
        cleaned_text, follow_ups = _extract_follow_ups(generated_text)

        # 9. Extract Citations & Validate
        cleaned_text, structured_citations = self.citation_service.extract_citations(cleaned_text, retrieved_articles)

        if not self.safety.validate_output(generated_text, set(retrieved_ids)):
            logger.warning("Safety Filter flagged the output for hallucinated citations.")

        # Add confidence labels to citations
        for cit in structured_citations:
            if cit.score >= 0.85:
                cit.confidence = "High"
            elif cit.score >= 0.65:
                cit.confidence = "Medium"
            else:
                cit.confidence = "Low"

        citations_dump = [c.model_dump() for c in structured_citations]
        yield StreamService.format_sse(StreamEventType.CITATION, {"citations": citations_dump})

        # 10. Yield follow-ups
        if follow_ups:
            yield StreamService.format_sse(StreamEventType.SUGGESTED_FOLLOW_UPS, {"follow_ups": follow_ups})

        yield StreamService.format_sse(StreamEventType.COMPLETED, {})

        # 11. Store Assistant Response in Memory
        assistant_msg = ChatMessage(role=ChatRole.ASSISTANT, content=cleaned_text, evidence=evidence_bundle)
        await self.memory.add_message(conversation_id, assistant_msg)

        # 12. Update conversation metadata
        msg_count = len(history) + 1  # +1 for the assistant response just added
        await self.registry.update_metadata(
            conversation_id,
            {"message_count": msg_count, "last_model": self.chat_model},
        )

        # 13. Background title generation after first assistant response
        if msg_count <= 2:
            title = await self._generate_title(conversation_id, cleaned_text)
            if title:
                yield StreamService.format_sse(StreamEventType.TITLE_GENERATED, {"title": title})

        # 14. Cache Response
        await self.cache.set(
            message,
            retrieved_ids,
            prompt_hash,
            self.chat_model,
            mode.value,
            {
                "text": cleaned_text,
                "citations": citations_dump,
                "follow_ups": follow_ups,
            },
        )

        # 15. Evaluate & Emit Metrics
        latency = int((time.time() - start_time) * 1000)
        metrics = RAGMetrics(
            latency_ms=latency,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=0.0,  # TODO: wire CostTracker
        )
        self.eval.log_metrics(conversation_id, metrics)
