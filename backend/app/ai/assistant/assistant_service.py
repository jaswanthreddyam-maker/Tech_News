import asyncio
import json
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.assistant.default_tools import register_default_tools
from app.ai.assistant.tools import AssistantToolRegistry
from app.ai.chat.stream_service import StreamService
from app.core.config import settings
from app.models.memory import ConversationEpisode

logger = logging.getLogger("tech_news.ai.assistant")

ASSISTANT_MAX_CONTEXT_MESSAGES = 6


GREETINGS_MAP: dict[str, str] = {
    "hi": "Hey there! What are you researching today?",
    "hello": "Hello! What technology or notes would you like to explore today?",
    "hey": "Hey! How can I assist with your research today?",
    "good morning": "Good morning! What tech news or research notes are on your mind today?",
    "good afternoon": "Good afternoon! How can I help with your research today?",
    "good evening": "Good evening! What would you like to research today?",
    "thanks": "You're welcome! Let me know if you need anything else researched.",
    "thank you": "Happy to help! Feel free to ask any follow-up questions.",
}


class PersonalAssistantService:
    def __init__(self, db: AsyncSession):
        self.db = db
        nvidia_key = getattr(settings, "NVIDIA_API_KEY", os.getenv("NVIDIA_API_KEY"))
        openai_key = getattr(settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        gemini_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))

        if nvidia_key and not nvidia_key.startswith("nvapi-placeholder"):
            nvidia_base_url = getattr(settings, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
            self.client = AsyncOpenAI(api_key=nvidia_key, base_url=nvidia_base_url)
            self.model = getattr(settings, "NVIDIA_MODEL", "openai/gpt-oss-120b")
        elif openai_key and not openai_key.startswith("sk-placeholder"):
            self.client = AsyncOpenAI(api_key=openai_key)
            self.model = getattr(settings, "CHAT_MODEL", "gpt-4o-mini")
        elif gemini_key and not gemini_key.startswith("mock-"):
            self.client = AsyncOpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            self.model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        else:
            self.client = None
            self.model = "gpt-4o-mini"

        self.registry = AssistantToolRegistry()
        register_default_tools(self.registry)

    async def stream_query(
        self,
        query: str,
        owner_type: str,
        owner_id: str,
        conversation_id: str | None = None,
        message_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        if not self.client:
            yield StreamService.format_error("AI provider not configured")
            return

        if not message_id:
            message_id = f"ast_msg_{uuid.uuid4().hex[:12]}"

        # Emit initial session frame if session identity is provided
        if conversation_id:
            yield f"event: session\ndata: {json.dumps({'conversation_id': conversation_id, 'message_id': message_id})}\n\n"

        # Deterministic lightweight path for simple conversational greetings
        clean_query = query.strip().lower().rstrip("!.,?")
        if clean_query in GREETINGS_MAP:
            greeting_text = GREETINGS_MAP[clean_query]
            # Stream tokens incrementally
            chunks = [greeting_text[i:i + 4] for i in range(0, len(greeting_text), 4)]
            for chunk in chunks:
                yield f"event: assistant_token\ndata: {json.dumps({'message_id': message_id, 'text': chunk})}\n\n"

            if conversation_id:
                try:
                    episode = ConversationEpisode(
                        conversation_id=conversation_id,
                        role="assistant",
                        message=greeting_text,
                        metadata_json={
                            "message_id": message_id,
                            "sources": [],
                            "owner_type": owner_type,
                            "owner_id": owner_id,
                        },
                        created_at=datetime.now(timezone.utc),
                    )
                    add_res = self.db.add(episode)
                    if hasattr(add_res, "__await__"):
                        await add_res
                    await self.db.commit()
                except Exception as e:
                    logger.error(f"Failed to persist greeting episode for {conversation_id}: {e}", exc_info=True)

            yield f"event: completed\ndata: {json.dumps({'message_id': message_id})}\n\n"
            return

        # Load recent chronological conversation history from DB (oldest -> newest)
        history_messages = []
        if conversation_id:
            try:
                stmt = (
                    select(ConversationEpisode)
                    .where(ConversationEpisode.conversation_id == conversation_id)
                    .order_by(ConversationEpisode.created_at.asc())
                )
                res = await self.db.execute(stmt)
                episodes = list(res.scalars().all())

                # Keep up to ASSISTANT_MAX_CONTEXT_MESSAGES (excluding current user query if saved)
                past_episodes = [ep for ep in episodes if not (ep.role == "user" and ep.message == query)][-ASSISTANT_MAX_CONTEXT_MESSAGES:]
                for ep in past_episodes:
                    history_messages.append({"role": ep.role.lower(), "content": ep.message})
            except Exception as e:
                logger.error(f"Failed to fetch conversation context for {conversation_id}: {e}", exc_info=True)

        system_prompt = (
            "You are a Personal AI Research Assistant for Tech News Today.\n\n"
            "CORE RESPONSIBILITIES:\n"
            "1. Answer questions by searching personal research notes, workspace documents, daily digests, "
            "and published global tech news using the available tools.\n"
            "2. Be concise, objective, and scannable. Prefer short paragraphs and structured bullet points.\n"
            "3. Structure news updates cleanly (e.g. '## NVIDIA — Recent developments', '- **Development:** ...', '- **Why it matters:** ...').\n"
            "4. Do NOT force information into markdown tables unless structured comparison genuinely improves readability.\n\n"
            "CRITICAL NEWS SAFETY RULE:\n"
            "If the user asks about recent, latest, current, or breaking news (e.g. 'recently', 'latest', 'today', 'this week') "
            "and the global Tech News corpus tool (search_global_tech_news) returns no evidence or empty results:\n"
            "- You MUST explicitly state that no recent coverage was found in the Tech News Today corpus.\n"
            "- Example: 'I couldn't find recent NVIDIA coverage in the Tech News Today corpus.'\n"
            "- You MUST NOT substitute or dump old pre-training model knowledge (e.g. 2024 or older history) as if it were recent news.\n"
            "- You may offer to search saved research notes or suggest broadening the search query."
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": query})
        # ── FAST PATH ────────────────────────────────────────────────────────────
        # For clearly global news queries: eagerly call search_global_tech_news
        # and inject results into the system message, then make ONE streaming LLM
        # call — saving ~7s vs the old two-round-trip approach.
        #
        # For personal/mixed queries ("my notes", "what do I know", etc.): fall
        # back to the full orchestration loop so the correct tools are invoked.
        # ────────────────────────────────────────────────────────────────────────
        _PERSONAL_SIGNALS = (
            "my ", "i saved", "i know", "my notes", "my research",
            "my knowledge", "what do i", "i've saved", "i have saved",
            "from my", "in my", "did i save", "i read",
        )
        _is_personal = any(sig in query.lower() for sig in _PERSONAL_SIGNALS)

        collected_sources = []

        if not _is_personal:
            # ── FAST PATH (global news query) ─────────────────────────────────
            try:
                yield f"event: tool_started\ndata: {json.dumps({'message_id': message_id, 'tool': 'search_global_tech_news', 'args': {'query': query}})}\n\n"
                from app.ai.assistant.default_tools import search_global_tech_news_executor
                search_result = await asyncio.wait_for(
                    search_global_tech_news_executor(query=query, db=self.db),
                    timeout=8.0,
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Fast-path search failed ({type(e).__name__}): {e}")
                search_result = "No articles found in the Tech News Today corpus for this query."

            yield f"event: tool_result\ndata: {json.dumps({'message_id': message_id, 'tool': 'search_global_tech_news'})}\n\n"

            # Parse sources card
            try:
                for obj_str in search_result.split("\n\n"):
                    obj_str = obj_str.strip()
                    if obj_str.startswith("{"):
                        item = json.loads(obj_str)
                        if isinstance(item, dict) and "title" in item:
                            collected_sources.append({
                                "title": item.get("title", ""),
                                "source": item.get("source", "Tech News Today"),
                                "url": item.get("url"),
                                "snippet": item.get("snippet", "")[:200],
                                "score": item.get("relevance_score", 0.0),
                            })
            except Exception:
                pass

            if collected_sources:
                yield f"event: sources\ndata: {json.dumps({'message_id': message_id, 'sources': collected_sources})}\n\n"

            # Inject corpus results into the system message so the user message
            # stays unmodified (preserves message structure expected by tests and
            # conversation history logic).
            messages[0]["content"] += (
                f"\n\n[RETRIEVED CORPUS CONTEXT]\n{search_result}\n[END CONTEXT]"
            )

        else:
            # ── ORCHESTRATION PATH (personal/mixed query) ─────────────────────
            tools_schema = self.registry.get_all_tools_schema()
            max_iterations = 5

            for iteration in range(max_iterations):
                try:
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            tools=tools_schema if tools_schema else None,
                            tool_choice="auto" if tools_schema else "none",
                            timeout=30.0,
                        ),
                        timeout=35.0,
                    )
                except asyncio.TimeoutError:
                    logger.error("Assistant LLM orchestration timed out after 35s")
                    yield StreamService.format_error("Request timed out. Please try again.")
                    return
                except Exception as e:
                    logger.error(f"Assistant LLM error: {e}")
                    yield StreamService.format_error("Provider error during orchestration")
                    return

                msg = response.choices[0].message

                if not msg.tool_calls:
                    break

                assistant_msg = {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        kwargs = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        kwargs = {}

                    yield f"event: tool_started\ndata: {json.dumps({'message_id': message_id, 'tool': name, 'args': kwargs})}\n\n"

                    result_str = await self.registry.execute_tool(
                        name=name, kwargs=kwargs, db=self.db, owner_type=owner_type, owner_id=owner_id
                    )

                    if result_str and name == "search_global_tech_news":
                        try:
                            parsed = json.loads(result_str)
                            items = parsed if isinstance(parsed, list) else [parsed]
                            for item in items:
                                if isinstance(item, dict) and "title" in item:
                                    collected_sources.append({
                                        "title": item.get("title", ""),
                                        "source": item.get("source", "Tech News Today"),
                                        "url": item.get("url"),
                                        "snippet": item.get("snippet", "")[:200],
                                        "score": item.get("relevance_score", 0.0),
                                    })
                        except (json.JSONDecodeError, TypeError):
                            pass

                    yield f"event: tool_result\ndata: {json.dumps({'message_id': message_id, 'tool': name})}\n\n"
                    messages.append({"role": "tool", "tool_call_id": tc.id, "name": name, "content": result_str})

            if collected_sources:
                yield f"event: sources\ndata: {json.dumps({'message_id': message_id, 'sources': collected_sources})}\n\n"

        # Final generation stream
        full_assistant_text = ""
        try:
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(model=self.model, messages=messages, stream=True, timeout=60.0),
                timeout=65.0,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    # STRICT FIX: Only user-facing content is streamed as assistant_token.
                    # Never fallback to internal model reasoning_content.
                    text_chunk = getattr(delta, "content", None)
                    if text_chunk:
                        full_assistant_text += text_chunk
                        yield f"event: assistant_token\ndata: {json.dumps({'message_id': message_id, 'text': text_chunk})}\n\n"

            # Persist assistant response episode in short-lived DB transaction
            if conversation_id and full_assistant_text:
                try:
                    episode = ConversationEpisode(
                        conversation_id=conversation_id,
                        role="assistant",
                        message=full_assistant_text,
                        metadata_json={
                            "message_id": message_id,
                            "sources": collected_sources,
                            "owner_type": owner_type,
                            "owner_id": owner_id,
                        },
                        created_at=datetime.now(timezone.utc),
                    )
                    add_res = self.db.add(episode)
                    if hasattr(add_res, "__await__"):
                        await add_res
                    await self.db.commit()
                except Exception as e:
                    logger.error(f"Failed to persist assistant episode for {conversation_id}: {e}", exc_info=True)
                    if hasattr(self.db, "rollback"):
                        rb_res = self.db.rollback()
                        if hasattr(rb_res, "__await__"):
                            await rb_res

            yield f"event: completed\ndata: {json.dumps({'message_id': message_id})}\n\n"

        except Exception as e:
            logger.error(f"Assistant generation error: {e}")
            yield StreamService.format_error("Generation failed")

